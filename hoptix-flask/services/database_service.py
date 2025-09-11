import uuid
import logging
from typing import Optional
from integrations.db_supabase import Supa

logger = logging.getLogger(__name__)

class DatabaseService:
    """High-level database operations for managing runs."""
    
    def __init__(self, db: Supa):
        self.db = db
    
    def validate_organization_exists(self, org_id: str) -> bool:
        """Validate that the organization exists in the database."""
        result = self.db.client.table("orgs").select("id").eq("id", org_id).limit(1).execute()
        exists = bool(result.data)
        if not exists:
            logger.error(f"Organization {org_id} not found in database")
        return exists
    
    def validate_location_exists(self, location_id: str, org_id: str) -> bool:
        """Validate that the location exists and belongs to the organization."""
        result = self.db.client.table("locations").select("id").eq("id", location_id).eq("org_id", org_id).limit(1).execute()
        exists = bool(result.data)
        if not exists:
            logger.error(f"Location {location_id} not found for organization {org_id}")
        return exists

    def create_run_for_date(self, org_id: str, location_id: str, run_date: str) -> str:
        """Create or get run for specific date. Validates org/location exist first."""
        # Validate inputs
        if not self.validate_organization_exists(org_id):
            raise ValueError(f"Organization {org_id} does not exist")
        
        if not self.validate_location_exists(location_id, org_id):
            raise ValueError(f"Location {location_id} does not exist or doesn't belong to org {org_id}")
        
        # Try to find existing run for this date and location
        existing = self.db.client.table("runs").select("id").eq(
            "location_id", location_id
        ).eq("run_date", run_date).limit(1).execute()
        
        if existing.data:
            run_id = existing.data[0]["id"]
            logger.info(f"Using existing run_id: {run_id} for date: {run_date}, org: {org_id}, location: {location_id}")
        else:
            run_id = str(uuid.uuid4())
            run_data = {
                "id": run_id,
                "org_id": org_id,
                "location_id": location_id,
                "run_date": run_date,
                "status": "uploaded"
            }
            self.db.client.table("runs").upsert(run_data, on_conflict="id").execute()
            logger.info(f"Created new run_id: {run_id} for date: {run_date}, org: {org_id}, location: {location_id}")
        
        return run_id
