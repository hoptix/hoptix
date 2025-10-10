"""
Authorization Helper Functions

Provides ownership verification for resources based on user_id.
"""

import logging
from flask import g
from services.database import Supa

logger = logging.getLogger(__name__)

# Initialize database connection
db = Supa()


def verify_location_ownership(user_id: str, location_id: str) -> bool:
    """
    Verify that a user owns a specific location

    Args:
        user_id (str): The user's ID (UUID)
        location_id (str): The location's ID (UUID)

    Returns:
        bool: True if user owns the location, False otherwise
    """
    try:
        # Admin users have access to all locations
        if hasattr(g, 'is_admin') and g.is_admin:
            logger.info(f"Admin user {user_id} granted access to location {location_id}")
            return True

        # Query locations table to check owner_id
        result = db.client.table("locations").select("owner_id").eq("id", location_id).single().execute()

        if not result.data:
            logger.warning(f"Location {location_id} not found")
            return False

        owner_id = result.data.get("owner_id")

        if owner_id == user_id:
            return True

        logger.warning(f"User {user_id} attempted to access location {location_id} owned by {owner_id}")
        return False

    except Exception as e:
        logger.error(f"Error verifying location ownership: {e}")
        return False


def verify_run_ownership(user_id: str, run_id: str) -> bool:
    """
    Verify that a user owns a specific run (through location ownership)

    Args:
        user_id (str): The user's ID (UUID)
        run_id (str): The run's ID (UUID)

    Returns:
        bool: True if user owns the run, False otherwise
    """
    try:
        # Admin users have access to all runs
        if hasattr(g, 'is_admin') and g.is_admin:
            logger.info(f"Admin user {user_id} granted access to run {run_id}")
            return True

        # Query runs table to get location_id
        run_result = db.client.table("runs").select("location_id").eq("id", run_id).single().execute()

        if not run_result.data:
            logger.warning(f"Run {run_id} not found")
            return False

        location_id = run_result.data.get("location_id")

        if not location_id:
            logger.error(f"Run {run_id} has no location_id")
            return False

        # Verify location ownership
        return verify_location_ownership(user_id, location_id)

    except Exception as e:
        logger.error(f"Error verifying run ownership: {e}")
        return False


def get_user_locations(user_id: str) -> list:
    """
    Get all locations owned by a user

    Args:
        user_id (str): The user's ID (UUID)

    Returns:
        list: List of location IDs (UUIDs) owned by the user
    """
    try:
        logger.info(f"get_user_locations called for user {user_id}")
        logger.info(f"g.is_admin exists: {hasattr(g, 'is_admin')}, value: {getattr(g, 'is_admin', 'N/A')}")

        # Admin users get access to ALL locations
        if hasattr(g, 'is_admin') and g.is_admin:
            logger.info(f"✓ Admin user {user_id} granted access to ALL locations")
            result = db.client.table("locations").select("id").execute()
            if not result.data:
                return []
            logger.info(f"Returning {len(result.data)} locations for admin")
            return [location["id"] for location in result.data]

        # Regular users only get their own locations
        logger.info(f"Regular user {user_id} - fetching owned locations only")
        result = db.client.table("locations").select("id").eq("owner_id", user_id).execute()

        if not result.data:
            return []

        return [location["id"] for location in result.data]

    except Exception as e:
        logger.error(f"Error fetching user locations: {e}")
        return []
