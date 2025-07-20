#!/usr/bin/env python3
"""
DNS Zone Database Operations (SCRUM-129)
Simple operations for managing DNS zone ownership tracking.
"""

import logging
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .connection import DatabaseManager
from .models import DNSZoneOwnership

logger = logging.getLogger(__name__)


class DNSZoneOwnershipOperations:
    """
    Database operations for DNS zone ownership tracking.
    
    Provides simple methods to track which zones belong to which users.
    """
    
    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize DNS zone operations.
        
        Args:
            db_manager: Database connection manager
        """
        self.db_manager = db_manager
    
    def create_zone_ownership(self, zone_name: str, user_id: str) -> Optional[DNSZoneOwnership]:
        """
        Create a zone ownership record.
        
        Args:
            zone_name: DNS zone name
            user_id: User ID who owns the zone
            
        Returns:
            DNSZoneOwnership object if created, None on error
        """
        try:
            with self.db_manager.get_session() as session:
                # Check if zone already exists
                existing = session.execute(
                    select(DNSZoneOwnership).where(DNSZoneOwnership.zone_name == zone_name)
                ).scalar_one_or_none()
                
                if existing:
                    logger.warning(f"Zone {zone_name} already has an owner: {existing.created_by}")
                    return None
                
                # Create new zone ownership
                zone = DNSZoneOwnership(zone_name=zone_name, created_by=user_id)
                session.add(zone)
                session.commit()
                
                logger.info(f"Created zone ownership: {zone_name} -> user {user_id}")
                return zone
                
        except IntegrityError as e:
            logger.error(f"Integrity error creating zone ownership: {e}")
            return None
        except SQLAlchemyError as e:
            logger.error(f"Database error creating zone ownership: {e}")
            return None
    
    def get_user_zones(self, user_id: str) -> List[str]:
        """
        Get all zones owned by a user.
        
        Args:
            user_id: User ID to get zones for
            
        Returns:
            List of zone names
        """
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(
                    select(DNSZoneOwnership.zone_name)
                    .where(DNSZoneOwnership.created_by == user_id)
                    .order_by(DNSZoneOwnership.zone_name)
                )
                
                zones = [row[0] for row in result.fetchall()]
                logger.debug(f"User {user_id} owns {len(zones)} zones")
                return zones
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting user zones: {e}")
            return []
    
    def check_zone_ownership(self, zone_name: str, user_id: str) -> bool:
        """
        Check if a user owns a zone.
        
        Args:
            zone_name: DNS zone name
            user_id: User ID to check
            
        Returns:
            True if user owns the zone, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(
                    select(DNSZoneOwnership)
                    .where(DNSZoneOwnership.zone_name == zone_name)
                    .where(DNSZoneOwnership.created_by == user_id)
                ).scalar_one_or_none()
                
                return result is not None
                
        except SQLAlchemyError as e:
            logger.error(f"Error checking zone ownership: {e}")
            return False
    
    def transfer_zone_ownership(self, zone_name: str, new_user_id: str) -> bool:
        """
        Transfer zone ownership to another user.
        
        Args:
            zone_name: DNS zone name
            new_user_id: New owner user ID
            
        Returns:
            True if transferred, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                zone = session.execute(
                    select(DNSZoneOwnership).where(DNSZoneOwnership.zone_name == zone_name)
                ).scalar_one_or_none()
                
                if not zone:
                    logger.error(f"Zone {zone_name} not found")
                    return False
                
                old_owner = zone.created_by
                zone.created_by = new_user_id
                session.commit()
                
                logger.info(f"Transferred zone {zone_name} from {old_owner} to {new_user_id}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error transferring zone ownership: {e}")
            return False
    
    def delete_zone_ownership(self, zone_name: str) -> bool:
        """
        Delete zone ownership record.
        
        Args:
            zone_name: DNS zone name
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            with self.db_manager.get_session() as session:
                zone = session.execute(
                    select(DNSZoneOwnership).where(DNSZoneOwnership.zone_name == zone_name)
                ).scalar_one_or_none()
                
                if not zone:
                    logger.warning(f"Zone {zone_name} not found for deletion")
                    return False
                
                session.delete(zone)
                session.commit()
                
                logger.info(f"Deleted zone ownership for {zone_name}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Error deleting zone ownership: {e}")
            return False
    
    def get_zone_owner(self, zone_name: str) -> Optional[str]:
        """
        Get the owner of a zone.
        
        Args:
            zone_name: DNS zone name
            
        Returns:
            User ID of owner, None if not found
        """
        try:
            with self.db_manager.get_session() as session:
                result = session.execute(
                    select(DNSZoneOwnership.created_by)
                    .where(DNSZoneOwnership.zone_name == zone_name)
                ).scalar_one_or_none()
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Error getting zone owner: {e}")
            return None