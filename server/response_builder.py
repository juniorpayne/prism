#!/usr/bin/env python3
"""
Response Builder for Prism DNS Server (SCRUM-15)
Creates consistent registration response messages.
"""

import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone
import json

logger = logging.getLogger(__name__)


class ResponseBuilderConfigError(Exception):
    """Exception raised for response builder configuration errors."""

    pass


class ResponseBuilderConfig:
    """Configuration for response builder."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize response builder configuration."""
        response_config = config.get("response", {})

        self.include_server_info = response_config.get("include_server_info", True)
        self.include_statistics = response_config.get("include_statistics", False)
        self.message_format = response_config.get("message_format", "detailed")
        self.server_name = response_config.get("server_name", "Prism DNS Server")
        self.server_version = response_config.get("server_version", "1.0")

        # Validate message format
        valid_formats = {"minimal", "detailed", "full"}
        if self.message_format not in valid_formats:
            raise ResponseBuilderConfigError(
                f"Invalid message_format: {self.message_format}. "
                f"Must be one of: {valid_formats}"
            )

        logger.info(
            f"Response builder configured: format={self.message_format}, "
            f"server_info={self.include_server_info}"
        )


class ResponseTemplate:
    """Template for building responses."""

    def __init__(
        self, template_type: str, required_fields: List[str], optional_fields: List[str] = None
    ):
        """
        Initialize response template.

        Args:
            template_type: Type of template ('success', 'error')
            required_fields: List of required field names
            optional_fields: List of optional field names
        """
        self.template_type = template_type
        self.required_fields = set(required_fields)
        self.optional_fields = set(optional_fields or [])

    def validate(self, data: Dict[str, Any]) -> bool:
        """
        Validate data against template.

        Args:
            data: Data to validate

        Returns:
            True if valid, False otherwise
        """
        data_fields = set(data.keys())

        # Check that all required fields are present
        missing_required = self.required_fields - data_fields
        if missing_required:
            logger.warning(f"Missing required fields: {missing_required}")
            return False

        return True

    def apply(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply template to data.

        Args:
            data: Data to apply template to

        Returns:
            Templated response
        """
        if not self.validate(data):
            raise ValueError("Data does not match template requirements")

        # Include all required and optional fields that are present
        allowed_fields = self.required_fields | self.optional_fields

        response = {}
        for field in allowed_fields:
            if field in data:
                response[field] = data[field]

        return response


class ResponseBuilder:
    """
    Builder for creating consistent registration response messages.

    Handles various response types and formats according to configuration.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize response builder.

        Args:
            config: Configuration dictionary
        """
        self.config = ResponseBuilderConfig(config)

        # Define response templates
        self._templates = {
            "success": ResponseTemplate(
                template_type="success",
                required_fields=["version", "type", "status", "message", "timestamp"],
                optional_fields=[
                    "result_type",
                    "hostname",
                    "ip_address",
                    "previous_ip",
                    "previous_status",
                    "server_info",
                    "statistics",
                    "processing_time_ms",
                ],
            ),
            "error": ResponseTemplate(
                template_type="error",
                required_fields=["version", "type", "status", "message", "timestamp"],
                optional_fields=[
                    "error_type",
                    "hostname",
                    "ip_address",
                    "retry_after",
                    "server_info",
                    "error_code",
                ],
            ),
        }

        logger.info("ResponseBuilder initialized")

    def build_success_response(
        self, result_type: str, hostname: str, ip_address: str, message: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Build a success response message.

        Args:
            result_type: Type of result (new_registration, ip_change, etc.)
            hostname: Hostname that was processed
            ip_address: IP address associated with hostname
            message: Success message
            **kwargs: Additional fields to include

        Returns:
            Success response dictionary
        """
        # Base response structure
        response = {
            "version": "1.0",
            "type": "response",
            "status": "success",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add core fields based on message format
        if self.config.message_format in ["detailed", "full"]:
            response.update(
                {"result_type": result_type, "hostname": hostname, "ip_address": ip_address}
            )

        # Add optional fields from kwargs
        for key, value in kwargs.items():
            if value is not None and key != "statistics":  # Statistics handled separately
                response[key] = value

        # Add server info if configured
        if self.config.include_server_info:
            response["server_info"] = self._build_server_info()

        # Add statistics if configured and provided
        if self.config.include_statistics and "statistics" in kwargs:
            response["statistics"] = kwargs["statistics"]

        # Apply template validation
        try:
            template = self._templates["success"]
            return template.apply(response)
        except ValueError as e:
            logger.error(f"Error applying success template: {e}")
            return self._build_minimal_success_response(message)

    def build_error_response(
        self, error_type: str, message: str, hostname: str = "", **kwargs
    ) -> Dict[str, Any]:
        """
        Build an error response message.

        Args:
            error_type: Type of error (validation_error, database_error, etc.)
            message: Error message
            hostname: Hostname associated with error (if any)
            **kwargs: Additional fields to include

        Returns:
            Error response dictionary
        """
        # Base response structure
        response = {
            "version": "1.0",
            "type": "response",
            "status": "error",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add error-specific fields
        if self.config.message_format in ["detailed", "full"]:
            response["error_type"] = error_type
            if hostname:
                response["hostname"] = hostname

        # Add optional fields from kwargs
        for key, value in kwargs.items():
            if value is not None:
                response[key] = value

        # Add server info if configured
        if self.config.include_server_info:
            response["server_info"] = self._build_server_info()

        # Apply template validation
        try:
            template = self._templates["error"]
            return template.apply(response)
        except ValueError as e:
            logger.error(f"Error applying error template: {e}")
            return self._build_minimal_error_response(message)

    def _build_server_info(self) -> Dict[str, Any]:
        """
        Build server information block.

        Returns:
            Server information dictionary
        """
        return {
            "server_name": self.config.server_name,
            "server_version": self.config.server_version,
            "message_format": self.config.message_format,
        }

    def _build_minimal_success_response(self, message: str) -> Dict[str, Any]:
        """Build minimal success response for fallback."""
        return {
            "version": "1.0",
            "type": "response",
            "status": "success",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _build_minimal_error_response(self, message: str) -> Dict[str, Any]:
        """Build minimal error response for fallback."""
        return {
            "version": "1.0",
            "type": "response",
            "status": "error",
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def validate_response(self, response: Dict[str, Any]) -> bool:
        """
        Validate response structure.

        Args:
            response: Response to validate

        Returns:
            True if valid, False otherwise
        """
        # Check required base fields
        required_fields = {"version", "type", "status", "message", "timestamp"}

        if not all(field in response for field in required_fields):
            return False

        # Check status value
        if response["status"] not in {"success", "error"}:
            return False

        # Check version
        if response["version"] != "1.0":
            return False

        # Check type
        if response["type"] != "response":
            return False

        return True

    def create_rate_limit_response(
        self, hostname: str, retry_after: int, current_rate: int, max_rate: int
    ) -> Dict[str, Any]:
        """
        Create rate limit exceeded response.

        Args:
            hostname: Hostname that triggered rate limit
            retry_after: Seconds to wait before retry
            current_rate: Current request rate
            max_rate: Maximum allowed rate

        Returns:
            Rate limit response dictionary
        """
        return self.build_error_response(
            error_type="rate_limit_exceeded",
            message=f"Rate limit exceeded: {current_rate}/{max_rate} requests per minute",
            hostname=hostname,
            retry_after=retry_after,
            current_rate=current_rate,
            max_rate=max_rate,
        )

    def create_validation_error_response(
        self, hostname: str, field: str, error_detail: str
    ) -> Dict[str, Any]:
        """
        Create validation error response.

        Args:
            hostname: Hostname that failed validation
            field: Field that failed validation
            error_detail: Detailed error message

        Returns:
            Validation error response dictionary
        """
        return self.build_error_response(
            error_type="validation_error",
            message=f"Validation failed for {field}: {error_detail}",
            hostname=hostname,
            failed_field=field,
            error_detail=error_detail,
        )

    def create_database_error_response(
        self, hostname: str, operation: str, error_detail: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create database error response.

        Args:
            hostname: Hostname associated with operation
            operation: Database operation that failed
            error_detail: Optional detailed error message

        Returns:
            Database error response dictionary
        """
        message = f"Database operation failed: {operation}"
        if error_detail:
            message += f" ({error_detail})"

        return self.build_error_response(
            error_type="database_error",
            message=message,
            hostname=hostname,
            failed_operation=operation,
        )

    def create_new_registration_response(
        self, hostname: str, ip_address: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Create new registration success response.

        Args:
            hostname: Registered hostname
            ip_address: Registered IP address
            **kwargs: Additional fields

        Returns:
            New registration response dictionary
        """
        return self.build_success_response(
            result_type="new_registration",
            hostname=hostname,
            ip_address=ip_address,
            message=f"New host '{hostname}' registered with IP {ip_address}",
            **kwargs,
        )

    def create_ip_change_response(
        self, hostname: str, new_ip: str, previous_ip: str, **kwargs
    ) -> Dict[str, Any]:
        """
        Create IP change success response.

        Args:
            hostname: Hostname with changed IP
            new_ip: New IP address
            previous_ip: Previous IP address
            **kwargs: Additional fields

        Returns:
            IP change response dictionary
        """
        return self.build_success_response(
            result_type="ip_change",
            hostname=hostname,
            ip_address=new_ip,
            previous_ip=previous_ip,
            message=f"IP address for '{hostname}' changed from {previous_ip} to {new_ip}",
            **kwargs,
        )

    def create_heartbeat_response(self, hostname: str, ip_address: str, **kwargs) -> Dict[str, Any]:
        """
        Create heartbeat update success response.

        Args:
            hostname: Hostname with heartbeat update
            ip_address: Current IP address
            **kwargs: Additional fields

        Returns:
            Heartbeat response dictionary
        """
        return self.build_success_response(
            result_type="heartbeat_update",
            hostname=hostname,
            ip_address=ip_address,
            message=f"Heartbeat updated for '{hostname}'",
            **kwargs,
        )

    def create_reconnection_response(
        self, hostname: str, ip_address: str, previous_status: str = "offline", **kwargs
    ) -> Dict[str, Any]:
        """
        Create reconnection success response.

        Args:
            hostname: Reconnected hostname
            ip_address: Current IP address
            previous_status: Previous host status
            **kwargs: Additional fields

        Returns:
            Reconnection response dictionary
        """
        return self.build_success_response(
            result_type="reconnection",
            hostname=hostname,
            ip_address=ip_address,
            previous_status=previous_status,
            message=f"Host '{hostname}' reconnected",
            **kwargs,
        )

    def get_builder_stats(self) -> Dict[str, Any]:
        """
        Get response builder statistics and configuration.

        Returns:
            Dictionary with builder information
        """
        return {
            "message_format": self.config.message_format,
            "include_server_info": self.config.include_server_info,
            "include_statistics": self.config.include_statistics,
            "server_name": self.config.server_name,
            "server_version": self.config.server_version,
            "templates_available": list(self._templates.keys()),
        }


def create_response_builder(config: Dict[str, Any]) -> ResponseBuilder:
    """
    Create a response builder instance.

    Args:
        config: Configuration dictionary

    Returns:
        Configured ResponseBuilder instance
    """
    return ResponseBuilder(config)
