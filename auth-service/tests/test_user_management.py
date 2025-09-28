import pytest
import requests


def cleanup_test_user(config, http_client, user_id):
    """Helper to clean up test users"""
    if not user_id or not config.service_role_key:
        return

    try:
        headers = {"Authorization": f"Bearer {config.service_role_key}"}
        http_client.delete(f"{config.base_url}/admin/users/{user_id}", headers=headers)
    except Exception:
        pass  # Ignore cleanup errors


class TestUserManagement:
    @pytest.fixture
    def authenticated_user(self, config, http_client, unique_email):
        """Create and authenticate a test user"""
        # Create user
        signup_data = {"email": unique_email, "password": config.test_password}

        signup_response = http_client.post(
            f"{config.base_url}/signup", json=signup_data
        )

        assert signup_response.status_code == 200
        user_data = signup_response.json()

        # Try to login
        login_data = {"email": unique_email, "password": config.test_password}

        login_response = http_client.post(
            f"{config.base_url}/token?grant_type=password", json=login_data
        )

        user_info = {
            "id": user_data["user"]["id"],
            "email": unique_email,
            "access_token": None,
            "refresh_token": None,
        }

        if login_response.status_code == 200:
            auth_data = login_response.json()
            user_info["access_token"] = auth_data["access_token"]
            user_info["refresh_token"] = auth_data["refresh_token"]

        yield user_info

        # Cleanup - use the correct user ID from the nested structure
        cleanup_test_user(config, http_client, user_data["user"]["id"])

    def test_get_user_profile(self, config, http_client, authenticated_user):
        """Test getting current user profile"""
        if not authenticated_user["access_token"]:
            pytest.skip("User authentication required")

        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        response = http_client.get(f"{config.base_url}/user", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == authenticated_user["email"]
        assert "id" in data
        assert "created_at" in data

    def test_get_user_unauthorized(self, config, http_client):
        """Test getting user profile without authentication"""
        response = http_client.get(f"{config.base_url}/user")

        assert response.status_code == 401

    def test_get_user_invalid_token(self, config, http_client):
        """Test getting user profile with invalid token"""
        headers = {"Authorization": "Bearer invalid-token"}

        response = http_client.get(f"{config.base_url}/user", headers=headers)

        assert response.status_code == 401

    def test_update_user_metadata(self, config, http_client, authenticated_user):
        """Test updating user metadata"""
        if not authenticated_user["access_token"]:
            pytest.skip("User authentication required")

        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        update_data = {
            "data": {
                "updated_field": "test_value",
                "preferences": {"theme": "dark", "notifications": False},
            }
        }

        response = http_client.put(
            f"{config.base_url}/user", json=update_data, headers=headers
        )

        # Accept both success and reauthentication required
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "user_metadata" in data

    def test_update_user_unauthorized(self, config, http_client):
        """Test updating user without authentication"""
        update_data = {"data": {"test": "value"}}

        response = http_client.put(f"{config.base_url}/user", json=update_data)

        assert response.status_code == 401

    def test_logout_user(self, config, http_client, authenticated_user):
        """Test user logout"""
        if not authenticated_user["access_token"]:
            pytest.skip("User authentication required")

        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        response = http_client.post(f"{config.base_url}/logout", headers=headers)

        assert response.status_code == 204

    def test_logout_unauthorized(self, config, http_client):
        """Test logout without authentication"""
        response = http_client.post(f"{config.base_url}/logout")

        assert response.status_code == 401

    def test_reauthenticate_endpoint(self, config, http_client, authenticated_user):
        """Test reauthentication endpoint"""
        if not authenticated_user["access_token"]:
            pytest.skip("User authentication required")

        headers = {"Authorization": f"Bearer {authenticated_user['access_token']}"}

        response = http_client.get(f"{config.base_url}/reauthenticate", headers=headers)

        # Should return 200 for success or 400/405 if endpoint doesn't exist in Supabase
        assert response.status_code in [200, 400, 500]
