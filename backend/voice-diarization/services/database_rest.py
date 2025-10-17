#!/usr/bin/env python3
"""
Database REST Client for Voice Diarization
Uses direct REST API calls to Supabase, avoiding SDK and Pydantic conflicts
Includes retry logic and defensive response parsing for reliability
"""

import os
import json
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import httpx
from functools import wraps

logger = logging.getLogger(__name__)


def retry_on_failure(retries: int = 3, delay: float = 5.0, backoff: float = 1.5):
    """
    Decorator to retry a function on failure with exponential backoff.

    Args:
        retries: Number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay on each retry
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {retries} attempts failed for {func.__name__}: {e}"
                        )

            # If all retries failed, raise the last exception
            raise last_exception

        return wrapper
    return decorator


class DatabaseClient:
    """
    Direct REST API client for Supabase.
    No SDK dependencies, no Pydantic conflicts.
    """

    def __init__(self):
        """Initialize the REST client with credentials."""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_SERVICE_KEY')

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set")

        # Remove trailing slash if present
        self.url = self.url.rstrip('/')
        self.base_url = f"{self.url}/rest/v1"

        # Configure HTTP client with retry logic
        self.client = httpx.Client(
            headers={
                'apikey': self.key,
                'Authorization': f'Bearer {self.key}',
                'Content-Type': 'application/json',
                'Prefer': 'return=representation'
            },
            timeout=30.0,
            follow_redirects=True
        )

        logger.info("Initialized database REST client")

    def __del__(self):
        """Clean up HTTP client."""
        if hasattr(self, 'client'):
            self.client.close()

    @retry_on_failure(retries=3, delay=5.0, backoff=1.5)
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Any] = None
    ) -> Any:
        """
        Make a REST API request with error handling and automatic retries.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path
            params: Query parameters
            data: Request body data

        Returns:
            Response data (parsed JSON)
        """
        url = f"{self.base_url}/{endpoint}"

        try:
            response = self.client.request(
                method=method,
                url=url,
                params=params,
                json=data if data else None
            )
            response.raise_for_status()

            # Return parsed JSON if there's content
            if response.text:
                return response.json()
            return None

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Request failed: {e}")
            raise

    def create_run(self, location_id: str, date: str, run_type: str = 'voice_diarization') -> str:
        """
        Create a new run record.

        Args:
            location_id: UUID of the location
            date: Date string (YYYY-MM-DD)
            run_type: Type of run (default: voice_diarization)

        Returns:
            Run ID
        """
        try:
            # Get org_id for the location
            location = self._request(
                'GET',
                'locations',
                params={'id': f'eq.{location_id}', 'select': 'org_id'}
            )

            if not location:
                raise ValueError(f"Location {location_id} not found")

            org_id = location[0]['org_id']

            # Create run record
            run_data = {
                'org_id': org_id,
                'location_id': location_id,
                'run_date': date,
                'status': 'processing',
                'type': run_type
            }

            result = self._request('POST', 'runs', data=run_data)

            if result and len(result) > 0:
                run_id = result[0]['id']
                logger.info(f"Created run {run_id} for location {location_id} on {date}")
                return run_id

            raise ValueError("Failed to create run record")

        except Exception as e:
            logger.error(f"Error creating run: {e}")
            raise

    def update_run(self, run_id: str, data: Dict[str, Any]) -> bool:
        """
        Update a run record.

        Args:
            run_id: Run ID to update
            data: Data to update

        Returns:
            Success boolean
        """
        try:
            # Add timestamp
            data['updated_at'] = datetime.now().isoformat()

            result = self._request(
                'PATCH',
                'runs',
                params={'id': f'eq.{run_id}'},
                data=data
            )

            return True

        except Exception as e:
            logger.error(f"Error updating run {run_id}: {e}")
            return False

    def get_transactions_for_date(
        self,
        location_id: str,
        date: str,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get all valid transactions for a location and date.
        Automatically filters out incomplete orders and already-labeled transactions.

        Args:
            location_id: Location UUID
            date: Date string (YYYY-MM-DD)
            limit: Maximum number of transactions

        Returns:
            List of transaction records ready for processing
        """
        try:
            # Query graded_rows_filtered view
            result = self._request(
                'GET',
                'graded_rows_filtered',
                params={
                    'location_id': f'eq.{location_id}',
                    'run_date': f'eq.{date}',
                    'select': 'transaction_id,grade_id,audio_s3_bucket,audio_s3_key,transcription,complete_order,worker_id',
                    'limit': limit,
                    'order': 'transaction_created_at'
                }
            )

            if not result:
                logger.info(f"No transactions found for {location_id} on {date}")
                return []

            # Filter out transactions that should be skipped
            valid_transactions = []
            skipped_incomplete = 0
            skipped_labeled = 0

            for transaction in result:
                # Skip if order not complete
                if not transaction.get('complete_order'):
                    skipped_incomplete += 1
                    continue

                # Skip if worker already labeled
                if transaction.get('worker_id') is not None:
                    skipped_labeled += 1
                    continue

                valid_transactions.append(transaction)

            logger.info(
                f"Found {len(result)} transactions for {location_id} on {date}: "
                f"{len(valid_transactions)} valid, {skipped_incomplete} incomplete, "
                f"{skipped_labeled} already labeled"
            )

            return valid_transactions

        except Exception as e:
            logger.error(f"Error fetching transactions: {e}")
            return []

    def update_transaction_worker(
        self,
        transaction_id: str,
        worker_id: Optional[str],
        confidence: float,
        assignment_source: str = 'voice'
    ) -> bool:
        """
        Update transaction with worker assignment.

        Args:
            transaction_id: Transaction ID
            worker_id: Worker ID (or None for no match)
            confidence: Confidence score (0-1)
            assignment_source: Source of assignment (default: 'voice')

        Returns:
            Success boolean
        """
        try:
            data = {
                'worker_id': worker_id,
                'worker_assignment_source': assignment_source,
                'worker_confidence': float(confidence),
                'voice_confidence': confidence,  # Keep for backward compatibility
                'voice_processed_at': datetime.now().isoformat()
            }

            result = self._request(
                'PATCH',
                'transactions',
                params={'id': f'eq.{transaction_id}'},
                data=data
            )

            return True

        except Exception as e:
            logger.error(f"Error updating transaction {transaction_id}: {e}")
            return False

    def get_workers(self) -> List[Dict[str, Any]]:
        """
        Get all workers from the database.

        Returns:
            List of worker records with id and legal_name
        """
        try:
            result = self._request(
                'GET',
                'workers',
                params={'select': 'id,legal_name'}
            )

            return result if result else []

        except Exception as e:
            logger.error(f"Error fetching workers: {e}")
            return []

    def get_location_name(self, location_id: str) -> Optional[str]:
        """
        Get location name by ID.

        Args:
            location_id: Location UUID

        Returns:
            Location name or None
        """
        try:
            result = self._request(
                'GET',
                'locations',
                params={'id': f'eq.{location_id}', 'select': 'name'}
            )

            if result and len(result) > 0:
                return result[0]['name']

            return None

        except Exception as e:
            logger.error(f"Error fetching location name: {e}")
            return None

    def should_skip_transaction(self, transaction_id: str) -> bool:
        """
        Check if a transaction should be skipped (not complete or already labeled).

        Args:
            transaction_id: Transaction ID to check

        Returns:
            True if transaction should be skipped, False otherwise
        """
        try:
            # Query graded_rows_filtered for this transaction
            result = self._request(
                'GET',
                'graded_rows_filtered',
                params={
                    'transaction_id': f'eq.{transaction_id}',
                    'select': 'complete_order,worker_id'
                }
            )

            # If transaction not found, skip it
            if not result or len(result) == 0:
                logger.debug(f"Transaction {transaction_id} not found in graded_rows_filtered. Skipping.")
                return True

            transaction = result[0]

            # Skip if order not complete
            if not transaction.get('complete_order'):
                logger.debug(f"Order for transaction {transaction_id} not complete. Skipping.")
                return True

            # Skip if worker already labeled
            if transaction.get('worker_id') is not None:
                logger.debug(f"Worker for transaction {transaction_id} already labeled. Skipping.")
                return True

            # Transaction is valid for processing
            return False

        except Exception as e:
            logger.error(f"Error checking transaction {transaction_id}: {e}")
            # If check fails, skip transaction to be safe
            return True

    def test_connection(self) -> bool:
        """
        Test database connectivity.

        Returns:
            True if connection is successful
        """
        try:
            # Try to query locations table with limit 1
            result = self._request(
                'GET',
                'locations',
                params={'select': 'id', 'limit': 1}
            )
            logger.info("✅ Database connection successful")
            return True

        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False