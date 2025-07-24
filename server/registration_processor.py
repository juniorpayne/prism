#!/usr/bin/env python3
"""
Registration Processor for Prism DNS Server (SCRUM-15)
Advanced host registration processing with IP change detection and logging.
"""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .database.connection import DatabaseManager
from .database.operations import HostOperations
from .message_validator import MessageValidator

logger = logging.getLogger(__name__)


class RegistrationConfigError(Exception):
    """Exception raised for registration configuration errors."""

    pass


@dataclass
class RegistrationResult:
    """Result of a host registration operation."""

    success: bool
    result_type: (
        str  # new_registration, ip_change, heartbeat_update, reconnection, validation_error, etc.
    )
    message: str
    hostname: str
    ip_address: str
    timestamp: str = None
    previous_ip: Optional[str] = None
    previous_status: Optional[str] = None
    processing_time_ms: Optional[float] = None
    auth_status: Optional[str] = None  # authenticated, anonymous, invalid_token

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return asdict(self)

    def to_json(self) -> str:
        """Convert result to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class RegistrationConfig:
    """Configuration for registration processor."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize registration configuration."""
        reg_config = config.get("registration", {})

        self.enable_ip_tracking = reg_config.get("enable_ip_tracking", True)
        self.enable_event_logging = reg_config.get("enable_event_logging", True)
        self.max_registrations_per_minute = reg_config.get("max_registrations_per_minute", 1000)
        self.duplicate_registration_window = reg_config.get("duplicate_registration_window", 5)
        self.enable_rate_limiting = reg_config.get("enable_rate_limiting", True)
        self.enable_validation = reg_config.get("enable_validation", True)
        
        # Validation
        if self.max_registrations_per_minute <= 0:
            raise RegistrationConfigError("max_registrations_per_minute must be positive")

        if self.duplicate_registration_window < 0:
            raise RegistrationConfigError("duplicate_registration_window must be non-negative")

        logger.info(
            f"Registration processor configured: ip_tracking={self.enable_ip_tracking}, "
            f"rate_limit={self.max_registrations_per_minute}/min"
        )


class RegistrationProcessor:
    """
    Advanced host registration processor.

    Handles various registration scenarios:
    - New host registration
    - Existing host heartbeat updates
    - IP address changes
    - Host reconnections from offline state
    - Validation and error handling
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize registration processor.

        Args:
            config: Configuration dictionary
        """
        self.config = RegistrationConfig(config)

        # Initialize database connection
        self.db_manager = DatabaseManager(config)
        self.db_manager.initialize_schema()
        self.host_ops = HostOperations(self.db_manager)

        # Initialize validator
        self.validator = MessageValidator()

        # Statistics tracking
        self._stats = {
            "total_registrations": 0,
            "new_registrations": 0,
            "heartbeat_updates": 0,
            "ip_changes": 0,
            "reconnections": 0,
            "validation_errors": 0,
            "database_errors": 0,
            "duplicate_registrations": 0,
            "authenticated_registrations": 0,
            "failed_auth_registrations": 0,
        }

        # Rate limiting tracking
        self._rate_limit_tracker = {}
        self._last_cleanup = time.time()

        # Duplicate detection tracking
        self._recent_registrations = {}
        
        # Token caching
        self._token_cache = {}  # Simple cache for token lookups
        self._cache_ttl = 300  # 5 minutes

        logger.info("RegistrationProcessor initialized")

    async def process_registration(
        self, hostname: str, client_ip: str, message_timestamp: str, user_id: str = None, auth_token: str = None
    ) -> RegistrationResult:
        """
        Process a host registration request.

        Args:
            hostname: Hostname to register
            client_ip: Client IP address
            message_timestamp: Timestamp from registration message
            user_id: User ID who owns this host registration (optional if auth_token provided)
            auth_token: Authentication token for TCP client (optional)

        Returns:
            RegistrationResult with operation details
        """
        # Authentication is always required
        if not auth_token:
            logger.warning(f"Rejecting unauthenticated registration from {hostname}")
            self._stats["failed_auth_registrations"] += 1
            return RegistrationResult(
                success=False,
                result_type="auth_required",
                message="Authentication required. Please configure auth_token.",
                hostname=hostname,
                ip_address=client_ip
            )
        
        # Validate auth token
        validation_result = await self._validate_token(auth_token, client_ip)
        if not validation_result['valid']:
            logger.warning(f"Invalid token provided for {hostname}: {validation_result['reason']}")
            self._stats["failed_auth_registrations"] += 1
            return RegistrationResult(
                success=False,
                result_type="invalid_token",
                message=f"Invalid authentication token: {validation_result['reason']}",
                hostname=hostname,
                ip_address=client_ip
            )
        
        # Authentication successful
        user_id = validation_result['user_id']
        auth_status = "authenticated"
        logger.info(f"Authenticated registration for user {user_id}")
        
        # Basic user ID format validation - allow UUIDs and test IDs
        import re
        # Match UUID format or test user IDs like "user-123" or "test-user-123"
        user_id_pattern = re.compile(r'^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}$|^[a-zA-Z0-9\-]+$')
        if not user_id_pattern.match(user_id):
            raise ValueError("Invalid user_id format")
        start_time = time.time()

        try:
            # Update statistics
            self._stats["total_registrations"] += 1

            # Rate limiting check
            if self.config.enable_rate_limiting:
                rate_limit_result = await self._check_rate_limit(client_ip)
                if not rate_limit_result.success:
                    return rate_limit_result

            # Validation
            if self.config.enable_validation:
                validation_result = await self._validate_registration(hostname, client_ip)
                if not validation_result.success:
                    self._stats["validation_errors"] += 1
                    return validation_result

            # Check for duplicate registration
            duplicate_result = await self._check_duplicate_registration(hostname, client_ip)
            if duplicate_result is not None:
                self._stats["duplicate_registrations"] += 1
                return duplicate_result

            # Process the registration based on host state
            result = await self._process_host_registration(hostname, client_ip, message_timestamp, user_id)

            # Add auth status to result
            result.auth_status = auth_status
            
            # Update metrics
            self._stats[f"{auth_status}_registrations"] = self._stats.get(f"{auth_status}_registrations", 0) + 1

            # Record the registration for duplicate detection
            await self._record_registration(hostname, client_ip)

            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            result.processing_time_ms = processing_time

            logger.info(
                f"Registration processed: {result.result_type} for {hostname} "
                f"({client_ip}) in {processing_time:.2f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Error processing registration for {hostname}: {e}")
            self._stats["database_errors"] += 1

            processing_time = (time.time() - start_time) * 1000

            return RegistrationResult(
                success=False,
                result_type="processing_error",
                message=f"Registration processing failed: {str(e)}",
                hostname=hostname,
                ip_address=client_ip,
                processing_time_ms=processing_time,
            )

    async def _validate_registration(self, hostname: str, client_ip: str) -> RegistrationResult:
        """
        Validate registration parameters.

        Args:
            hostname: Hostname to validate
            client_ip: IP address to validate

        Returns:
            RegistrationResult indicating validation success or failure
        """
        # Validate hostname
        is_valid, error = self.validator.validate_hostname(hostname)
        if not is_valid:
            return RegistrationResult(
                success=False,
                result_type="validation_error",
                message=f"Invalid hostname: {error}",
                hostname=hostname,
                ip_address=client_ip,
            )

        # Validate IP address
        is_valid, error = self.validator.validate_ip_address(client_ip)
        if not is_valid:
            return RegistrationResult(
                success=False,
                result_type="validation_error",
                message=f"Invalid IP address: {error}",
                hostname=hostname,
                ip_address=client_ip,
            )

        return RegistrationResult(
            success=True,
            result_type="validation_success",
            message="Validation passed",
            hostname=hostname,
            ip_address=client_ip,
        )

    async def _check_rate_limit(self, client_ip: str) -> RegistrationResult:
        """
        Check rate limiting for client IP.

        Args:
            client_ip: Client IP address

        Returns:
            RegistrationResult indicating rate limit status
        """
        current_time = time.time()

        # Cleanup old entries
        if current_time - self._last_cleanup > 60:  # Cleanup every minute
            await self._cleanup_rate_tracker()
            self._last_cleanup = current_time

        # Check current rate for this IP
        if client_ip not in self._rate_limit_tracker:
            self._rate_limit_tracker[client_ip] = []

        # Remove old entries (older than 1 minute)
        minute_ago = current_time - 60
        self._rate_limit_tracker[client_ip] = [
            timestamp for timestamp in self._rate_limit_tracker[client_ip] if timestamp > minute_ago
        ]

        # Check if rate limit exceeded
        if len(self._rate_limit_tracker[client_ip]) >= self.config.max_registrations_per_minute:
            return RegistrationResult(
                success=False,
                result_type="rate_limit_exceeded",
                message=f"Rate limit exceeded: {self.config.max_registrations_per_minute} registrations per minute",
                hostname="",
                ip_address=client_ip,
            )

        # Record this registration
        self._rate_limit_tracker[client_ip].append(current_time)

        return RegistrationResult(
            success=True,
            result_type="rate_limit_passed",
            message="Rate limit check passed",
            hostname="",
            ip_address=client_ip,
        )

    async def _check_duplicate_registration(
        self, hostname: str, client_ip: str
    ) -> Optional[RegistrationResult]:
        """
        Check for duplicate registrations within time window.

        Args:
            hostname: Hostname to check
            client_ip: Client IP address

        Returns:
            RegistrationResult if duplicate detected, None otherwise
        """
        if self.config.duplicate_registration_window <= 0:
            return None

        current_time = time.time()
        registration_key = f"{hostname}:{client_ip}"

        # Check if we have a recent registration for this hostname/IP
        if registration_key in self._recent_registrations:
            last_registration = self._recent_registrations[registration_key]
            time_diff = current_time - last_registration

            if time_diff < self.config.duplicate_registration_window:
                return RegistrationResult(
                    success=True,
                    result_type="duplicate_ignored",
                    message=f"Duplicate registration ignored (within {self.config.duplicate_registration_window}s window)",
                    hostname=hostname,
                    ip_address=client_ip,
                )

        return None

    async def _record_registration(self, hostname: str, client_ip: str) -> None:
        """Record registration for duplicate detection."""
        registration_key = f"{hostname}:{client_ip}"
        self._recent_registrations[registration_key] = time.time()

    async def _process_host_registration(
        self, hostname: str, client_ip: str, message_timestamp: str, user_id: str
    ) -> RegistrationResult:
        """
        Process host registration based on current host state.

        Args:
            hostname: Hostname to register
            client_ip: Client IP address
            message_timestamp: Registration timestamp
            user_id: User ID who owns this host

        Returns:
            RegistrationResult with operation details
        """
        # Check if host exists for this user (user-scoped hostname namespace)
        existing_host = self.host_ops.get_host_by_hostname(hostname, user_id)

        if existing_host is None:
            # New host registration
            return await self._process_new_host_registration(hostname, client_ip, user_id)
        else:
            # Existing host - check what type of update this is
            return await self._process_existing_host_registration(
                existing_host, hostname, client_ip, message_timestamp, user_id
            )

    async def _process_new_host_registration(
        self, hostname: str, client_ip: str, user_id: str
    ) -> RegistrationResult:
        """
        Process new host registration.

        Args:
            hostname: Hostname to register
            client_ip: Client IP address
            user_id: User ID who owns this host

        Returns:
            RegistrationResult with operation details
        """
        try:
            # Create new host record
            new_host = self.host_ops.create_host(hostname, client_ip, user_id)

            if new_host:
                self._stats["new_registrations"] += 1

                logger.info(f"New host registered: {hostname} ({client_ip})")

                return RegistrationResult(
                    success=True,
                    result_type="new_registration",
                    message=f"New host registered with IP {client_ip}",
                    hostname=hostname,
                    ip_address=client_ip,
                )
            else:
                return RegistrationResult(
                    success=False,
                    result_type="database_error",
                    message="Failed to create host record in database",
                    hostname=hostname,
                    ip_address=client_ip,
                )

        except Exception as e:
            logger.error(f"Error creating new host {hostname}: {e}")
            return RegistrationResult(
                success=False,
                result_type="database_error",
                message=f"Database error: {str(e)}",
                hostname=hostname,
                ip_address=client_ip,
            )

    async def _process_existing_host_registration(
        self, existing_host, hostname: str, client_ip: str, message_timestamp: str, user_id: str
    ) -> RegistrationResult:
        """
        Process registration for existing host.

        Args:
            existing_host: Existing host record
            hostname: Hostname to register
            client_ip: Client IP address
            message_timestamp: Registration timestamp
            user_id: User ID making the registration

        Returns:
            RegistrationResult with operation details
        """
        # Verify the user owns this host
        if existing_host.created_by != user_id:
            return RegistrationResult(
                success=False,
                result_type="authorization_error",
                message="You are not authorized to update this host",
                hostname=hostname,
                ip_address=client_ip,
            )
        try:
            previous_ip = existing_host.current_ip
            previous_status = existing_host.status

            # Check if this is a reconnection (host was offline)
            if existing_host.status == "offline":
                # Host reconnection
                if existing_host.current_ip != client_ip:
                    # IP changed during offline period
                    success = self.host_ops.update_host_ip(hostname, client_ip)
                    if success:
                        self.host_ops.update_host_last_seen(hostname)
                        self._stats["reconnections"] += 1
                        self._stats["ip_changes"] += 1

                        logger.info(
                            f"Host reconnected with IP change: {hostname} "
                            f"{previous_ip} -> {client_ip}"
                        )

                        return RegistrationResult(
                            success=True,
                            result_type="reconnection",
                            message=f"Host reconnected with IP change from {previous_ip} to {client_ip}",
                            hostname=hostname,
                            ip_address=client_ip,
                            previous_ip=previous_ip,
                            previous_status=previous_status,
                        )
                else:
                    # Same IP, just reconnection
                    success = self.host_ops.update_host_last_seen(hostname)
                    if success:
                        # Mark host as online (implicit in update_host_last_seen)
                        self._stats["reconnections"] += 1

                        logger.info(f"Host reconnected: {hostname} ({client_ip})")

                        return RegistrationResult(
                            success=True,
                            result_type="reconnection",
                            message=f"Host reconnected",
                            hostname=hostname,
                            ip_address=client_ip,
                            previous_status=previous_status,
                        )

            elif existing_host.current_ip != client_ip:
                # IP address changed
                success = self.host_ops.update_host_ip(hostname, client_ip)
                if success:
                    self.host_ops.update_host_last_seen(hostname)
                    self._stats["ip_changes"] += 1

                    logger.info(f"IP address changed: {hostname} {previous_ip} -> {client_ip}")

                    return RegistrationResult(
                        success=True,
                        result_type="ip_change",
                        message=f"IP address changed from {previous_ip} to {client_ip}",
                        hostname=hostname,
                        ip_address=client_ip,
                        previous_ip=previous_ip,
                    )
            else:
                # Same IP, heartbeat update
                success = self.host_ops.update_host_last_seen(hostname)
                if success:
                    self._stats["heartbeat_updates"] += 1

                    logger.debug(f"Heartbeat updated: {hostname} ({client_ip})")

                    return RegistrationResult(
                        success=True,
                        result_type="heartbeat_update",
                        message="Heartbeat updated",
                        hostname=hostname,
                        ip_address=client_ip,
                    )

            # If we get here, database operation failed
            return RegistrationResult(
                success=False,
                result_type="database_error",
                message="Failed to update host record in database",
                hostname=hostname,
                ip_address=client_ip,
            )

        except Exception as e:
            logger.error(f"Error updating existing host {hostname}: {e}")
            return RegistrationResult(
                success=False,
                result_type="database_error",
                message=f"Database error: {str(e)}",
                hostname=hostname,
                ip_address=client_ip,
            )

    async def _cleanup_rate_tracker(self) -> None:
        """Clean up old rate tracking entries."""
        current_time = time.time()
        minute_ago = current_time - 60

        # Clean up rate limit tracker
        for client_ip in list(self._rate_limit_tracker.keys()):
            self._rate_limit_tracker[client_ip] = [
                timestamp
                for timestamp in self._rate_limit_tracker[client_ip]
                if timestamp > minute_ago
            ]

            # Remove empty entries
            if not self._rate_limit_tracker[client_ip]:
                del self._rate_limit_tracker[client_ip]

        # Clean up duplicate registration tracker
        window_ago = current_time - self.config.duplicate_registration_window
        for reg_key in list(self._recent_registrations.keys()):
            if self._recent_registrations[reg_key] < window_ago:
                del self._recent_registrations[reg_key]

    def get_registration_stats(self) -> Dict[str, Any]:
        """
        Get registration processing statistics.

        Returns:
            Dictionary with statistics
        """
        return self._stats.copy()

    async def _validate_token(self, token: str, client_ip: str) -> Dict[str, Any]:
        """
        Validate API token and return user info.
        
        Args:
            token: API token to validate
            client_ip: Client IP address for tracking
            
        Returns:
            Dictionary with validation result
        """
        import hashlib
        from datetime import datetime, timezone
        from server.auth.models import APIToken
        
        # Check cache first
        cache_key = hashlib.sha256(token.encode()).hexdigest()
        if cache_key in self._token_cache:
            cached = self._token_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['result']
        
        # Database lookup
        with self.db_manager.get_session() as db:
            try:
                # Find all active tokens (we need to check each one since we store hashes)
                tokens = db.query(APIToken).filter(APIToken.is_active == True).all()
                
                for api_token in tokens:
                    if api_token.verify_token(token):
                        # Check if token is valid
                        if not api_token.is_valid():
                            return {
                                'valid': False,
                                'reason': 'token_expired' if api_token.expires_at else 'token_inactive'
                            }
                        
                        # Update token usage
                        api_token.last_used_at = datetime.now(timezone.utc)
                        api_token.last_used_ip = client_ip
                        db.commit()
                        
                        # Cache the result
                        result = {
                            'valid': True,
                            'user_id': str(api_token.user_id),
                            'token_id': str(api_token.id)
                        }
                        self._token_cache[cache_key] = {
                            'result': result,
                            'timestamp': time.time()
                        }
                        
                        return result
                
                # Token not found
                return {'valid': False, 'reason': 'token_not_found'}
                
            except Exception as e:
                logger.error(f"Token validation error: {e}")
                return {'valid': False, 'reason': 'validation_error'}


    def reset_statistics(self) -> None:
        """Reset all statistics counters."""
        for key in self._stats:
            self._stats[key] = 0

        logger.info("Registration statistics reset")

    def cleanup(self) -> None:
        """Clean up resources."""
        if self.db_manager:
            self.db_manager.cleanup()

        logger.info("RegistrationProcessor cleanup completed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()


def create_registration_processor(config: Dict[str, Any]) -> RegistrationProcessor:
    """
    Create a registration processor instance.

    Args:
        config: Configuration dictionary

    Returns:
        Configured RegistrationProcessor instance
    """
    return RegistrationProcessor(config)
