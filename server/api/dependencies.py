#!/usr/bin/env python3
"""
FastAPI Dependencies (SCRUM-17)
Dependency injection for database and other services.
"""

import logging
from typing import Dict, Any, Generator
from fastapi import Depends, HTTPException, status
from server.database.connection import DatabaseManager
from server.database.operations import HostOperations

logger = logging.getLogger(__name__)

# Global configuration - will be set by app initialization
_app_config: Dict[str, Any] = {}


def set_app_config(config: Dict[str, Any]) -> None:
    """
    Set application configuration for dependency injection.
    
    Args:
        config: Application configuration
    """
    global _app_config
    _app_config = config
    logger.info("Application configuration set for API dependencies")


def get_app_config() -> Dict[str, Any]:
    """
    Get application configuration.
    
    Returns:
        Application configuration dictionary
    """
    if not _app_config:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Application configuration not initialized"
        )
    return _app_config


def get_database_manager(
    config: Dict[str, Any] = Depends(get_app_config)
) -> Generator[DatabaseManager, None, None]:
    """
    Get database manager dependency.
    
    Args:
        config: Application configuration
        
    Yields:
        DatabaseManager instance
    """
    db_manager = None
    try:
        db_manager = DatabaseManager(config)
        db_manager.initialize_schema()
        yield db_manager
    except Exception as e:
        logger.error(f"Database manager error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection error"
        )
    finally:
        if db_manager:
            try:
                db_manager.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up database manager: {e}")


def get_host_operations(
    db_manager: DatabaseManager = Depends(get_database_manager)
) -> HostOperations:
    """
    Get host operations dependency.
    
    Args:
        db_manager: Database manager instance
        
    Returns:
        HostOperations instance
    """
    try:
        return HostOperations(db_manager)
    except Exception as e:
        logger.error(f"Host operations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Host operations initialization error"
        )