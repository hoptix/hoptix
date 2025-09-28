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


class TestAdminLogin:
    def test_admin_login_missing_email(self, config, http_client):
        """Test admin login without email"""
        login_data = {"password": config.test_password}

        response = http_client.post(f"{config.base_url}/login-admin", json=login_data)

        assert response.status_code == 400
        data = response.json()
        assert "code" in data
        assert "msg" in data or "message" in data

    def test_admin_login_missing_password(self, config, http_client):
        """Test admin login without password"""
        login_data = {"email": config.test_email}

        response = http_client.post(f"{config.base_url}/login-admin", json=login_data)

        assert response.status_code == 400
        data = response.json()
        assert "code" in data
        assert "msg" in data or "message" in data

    def test_admin_login_invalid_credentials(self, config, http_client):
        """Test admin login with invalid credentials"""
        login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

        response = http_client.post(f"{config.base_url}/login-admin", json=login_data)

        # Should fail at the login step
        assert response.status_code == 400

    def test_admin_login_endpoint_exists(self, config, http_client):
        """Test that the admin login endpoint exists and returns appropriate response"""
        login_data = {"email": "test@example.com", "password": "password123"}

        response = http_client.post(f"{config.base_url}/login-admin", json=login_data)

        # Should not return 404 (endpoint exists)
        assert response.status_code != 404
        # Should return either 400 (bad request) or other auth error
        assert response.status_code in [400, 401, 403, 422, 500]

    def test_admin_login_invalid_json(self, config, http_client):
        """Test admin login with invalid JSON"""
        response = http_client.post(
            f"{config.base_url}/login-admin",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "code" in data
        assert data["code"] == 400
