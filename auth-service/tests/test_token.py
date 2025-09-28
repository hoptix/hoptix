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


class TestToken:
    @pytest.fixture
    def created_user(self, config, http_client, unique_email):
        """Create a test user for login tests"""
        signup_data = {"email": unique_email, "password": config.test_password}
        

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)
        print(response.json())
        assert response.status_code in [200, 422, 429]
        user_data = response.json()["user"]

        yield {
            "id": user_data["id"],
            "email": unique_email,
            "password": config.test_password,
        }

        # Cleanup
        cleanup_test_user(config, http_client, user_data["id"])

    def test_login_with_password_grant_json(self, config, http_client, created_user):
        """Test login with password grant type using JSON"""
        login_data = {
            "email": created_user["email"],
            "password": created_user["password"],
        }

        response = http_client.post(
            f"{config.base_url}/token?grant_type=password", json=login_data
        )

        # Login might fail if email confirmation is required
        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert data["token_type"] == "bearer"
            assert "expires_in" in data

            if "user" in data:
                assert data["user"]["email"] == created_user["email"]
        else:
            # Email confirmation likely required
            assert response.status_code == 400
            data = response.json()
            assert "code" in data

    def test_login_with_password_grant_form(self, config, http_client, created_user):
        """Test login with password grant type using form data"""
        form_data = {
            "email": created_user["email"],
            "password": created_user["password"],
        }

        response = http_client.post(
            f"{config.base_url}/token?grant_type=password",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        # Accept both success and email confirmation required
        assert response.status_code in [200, 400]

        if response.status_code == 200:
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data

    def test_login_invalid_credentials(self, config, http_client, created_user):
        """Test login with invalid password"""
        login_data = {"email": created_user["email"], "password": "wrongpassword"}

        response = http_client.post(
            f"{config.base_url}/token?grant_type=password", json=login_data
        )

        assert response.status_code == 400
        data = response.json()
        assert "code" in data
        assert "msg" in data

    def test_login_nonexistent_user(self, config, http_client):
        """Test login with non-existent email"""
        login_data = {
            "email": "nonexistent@example.com",
            "password": config.test_password,
        }

        response = http_client.post(
            f"{config.base_url}/token?grant_type=password", json=login_data
        )

        assert response.status_code == 400

    def test_login_missing_grant_type(self, config, http_client, created_user):
        """Test login without grant_type parameter"""
        login_data = {
            "email": created_user["email"],
            "password": created_user["password"],
        }

        response = http_client.post(
            f"{config.base_url}/token", json=login_data  # No grant_type
        )

        assert response.status_code == 400

    def test_refresh_token_flow(self, config, http_client, created_user):
        """Test refresh token functionality"""
        # First, try to login to get tokens
        login_data = {
            "email": created_user["email"],
            "password": created_user["password"],
        }

        login_response = http_client.post(
            f"{config.base_url}/token?grant_type=password", json=login_data
        )

        # Skip if email confirmation is required
        if login_response.status_code != 200:
            pytest.skip("Email confirmation required for login")

        login_data = login_response.json()
        refresh_token = login_data["refresh_token"]

        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}

        refresh_response = http_client.post(
            f"{config.base_url}/token?grant_type=refresh_token", json=refresh_data
        )

        assert refresh_response.status_code == 200
        refresh_data = refresh_response.json()

        assert "access_token" in refresh_data
        assert "refresh_token" in refresh_data
        assert refresh_data["token_type"] == "bearer"

    def test_invalid_refresh_token(self, config, http_client):
        """Test refresh with invalid token"""
        refresh_data = {"refresh_token": "invalid-refresh-token"}

        response = http_client.post(
            f"{config.base_url}/token?grant_type=refresh_token", json=refresh_data
        )

        assert response.status_code == 400
