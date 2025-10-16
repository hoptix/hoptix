"""
Lightweight Supabase client for voice diarization.
Avoids realtime imports that cause Pydantic compatibility issues.
"""

import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SupaVoice:
    """
    Minimal Supabase client for voice diarization that only uses the REST API.
    Avoids importing realtime features that cause Pydantic v1/v2 conflicts.
    """

    def __init__(self):
        """Initialize the database client with minimal imports."""
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_SERVICE_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        # Try to import supabase, but fall back to direct REST API if needed
        try:
            # Only import what we need to avoid realtime issues
            from supabase import create_client
            from supabase.client import Client

            # Create client without realtime features
            self.client: Client = create_client(self.url, self.key)
            self.use_rest_fallback = False
            logger.info("Initialized Supabase client successfully")

        except ImportError as e:
            logger.warning(f"Could not import supabase client: {e}")
            logger.warning("Falling back to direct REST API calls")
            self.use_rest_fallback = True
            self._init_rest_client()

    def _init_rest_client(self):
        """Initialize a simple REST client as fallback."""
        import requests
        self.session = requests.Session()
        self.session.headers.update({
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        })
        self.base_url = f"{self.url}/rest/v1"

    def _rest_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a REST API request directly."""
        url = f"{self.base_url}/{endpoint}"
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json() if response.text else {}

    def get_location_name(self, location_id: str) -> Optional[str]:
        """Get location name by ID."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("locations").select("name").eq("id", location_id).execute()
                if result.data and len(result.data) > 0:
                    return result.data[0]["name"]
            else:
                # REST fallback
                result = self._rest_request(
                    "GET",
                    f"locations?id=eq.{location_id}&select=name"
                )
                if result and len(result) > 0:
                    return result[0]["name"]

            return None

        except Exception as e:
            logger.error(f"Failed to get location name: {e}")
            return None

    def get_workers(self) -> List[Dict[str, Any]]:
        """Get all workers from database."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("workers").select("id, legal_name").execute()
                return result.data if result.data else []
            else:
                # REST fallback
                result = self._rest_request("GET", "workers?select=id,legal_name")
                return result if isinstance(result, list) else []

        except Exception as e:
            logger.error(f"Failed to get workers: {e}")
            return []

    def check_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Check transaction status in graded_rows_filtered."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("graded_rows_filtered").select("*").eq(
                    "transaction_id", transaction_id
                ).execute()
                return result.data[0] if result.data else {}
            else:
                # REST fallback
                result = self._rest_request(
                    "GET",
                    f"graded_rows_filtered?transaction_id=eq.{transaction_id}"
                )
                return result[0] if result else {}

        except Exception as e:
            logger.error(f"Failed to check transaction {transaction_id}: {e}")
            return {}

    def update_transaction(self, transaction_id: str, data: Dict[str, Any]) -> bool:
        """Update transaction with worker assignment."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("transactions").update(data).eq("id", transaction_id).execute()
                return bool(result.data)
            else:
                # REST fallback
                import json
                result = self._rest_request(
                    "PATCH",
                    f"transactions?id=eq.{transaction_id}",
                    data=json.dumps(data)
                )
                return True

        except Exception as e:
            logger.error(f"Failed to update transaction {transaction_id}: {e}")
            return False

    def insert_run(self, data: Dict[str, Any]) -> Optional[str]:
        """Insert a new run record."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("runs").insert(data).execute()
                return result.data[0]["id"] if result.data else None
            else:
                # REST fallback
                import json
                result = self._rest_request(
                    "POST",
                    "runs",
                    data=json.dumps(data)
                )
                return result[0]["id"] if result else None

        except Exception as e:
            logger.error(f"Failed to insert run: {e}")
            return None

    def update_run(self, run_id: str, data: Dict[str, Any]) -> bool:
        """Update a run record."""
        try:
            if not self.use_rest_fallback:
                result = self.client.table("runs").update(data).eq("id", run_id).execute()
                return bool(result.data)
            else:
                # REST fallback
                import json
                result = self._rest_request(
                    "PATCH",
                    f"runs?id=eq.{run_id}",
                    data=json.dumps(data)
                )
                return True

        except Exception as e:
            logger.error(f"Failed to update run {run_id}: {e}")
            return False


# For backward compatibility, create an alias
Supa = SupaVoice