import os
import pytest
import requests
import time
from typing import Dict, Optional
from dotenv import load_dotenv
import random

load_dotenv()


class TestConfig:
    def __init__(self):
        self.base_url = os.getenv("TEST_BASE_URL", "http://localhost:8080")
        self.supabase_url = os.getenv("SUPABASE_URL", "")
        self.supabase_key = os.getenv("SUPABASE_ANON_KEY", "")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        self.test_email = os.getenv("TEST_EMAIL", "test@example.com")
        self.test_password = os.getenv("TEST_PASSWORD", "testPassword123!")
        self.test_phone = os.getenv("TEST_PHONE_NUMBER", "+1234567890")

        # Validate required config
        if not all([self.supabase_url, self.supabase_key]):
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY are required")


class TestUser:
    def __init__(self):
        self.id: Optional[str] = None
        self.email: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None


@pytest.fixture(scope="session")
def config():
    return TestConfig()


@pytest.fixture(scope="session")
def http_client():
    session = requests.Session()
    session.timeout = 30
    return session


@pytest.fixture(scope="function")
def test_user():
    return TestUser()


@pytest.fixture(scope="function")
def unique_email():
    """Generate a unique email for each test. Must be a valid email address."""
    timestamp = int(time.time())
    return f"test-{timestamp}-{random.randint(1000, 9999)}@gmail.com"


def cleanup_test_user(config: TestConfig, http_client: requests.Session, user_id: str):
    """Helper to clean up test users"""
    if not user_id or not config.service_role_key:
        return

    try:
        headers = {"Authorization": f"Bearer {config.service_role_key}"}
        http_client.delete(f"{config.base_url}/admin/users/{user_id}", headers=headers)
    except Exception:
        pass  # Ignore cleanup errors
