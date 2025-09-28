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


class TestSignup:
    def test_signup_with_email_password_success(
        self, config, http_client, unique_email
    ):
        """Test successful user signup with email and password"""
        signup_data = {
            "email": unique_email,
            "password": config.test_password,
            "data": {"first_name": "Test", "last_name": "User"},
        }

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "id" in data["user"]
        assert data["user"]["email"] == unique_email
        assert "created_at" in data["user"]
        assert "updated_at" in data["user"]

        # Cleanup
        cleanup_test_user(config, http_client, data.get("id"))

    def test_signup_with_metadata(self, config, http_client, unique_email):
        """Test signup with custom user metadata"""
        metadata = {
            "role": "tester",
            "department": "QA",
            "preferences": {"theme": "dark", "notifications": True},
        }

        signup_data = {
            "email": unique_email,
            "password": config.test_password,
            "data": metadata,
        }

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 200
        data = response.json()

        # Verify user was created
        assert data["user"]["email"] == unique_email

        # Cleanup
        cleanup_test_user(config, http_client, data.get("id"))

    def test_signup_invalid_email_format(self, config, http_client):
        """Test signup with invalid email format"""
        signup_data = {
            "email": "invalid-email-format",
            "password": config.test_password,
        }

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 400
        data = response.json()
        assert "code" in data
        assert "msg" in data

    def test_signup_weak_password(self, config, http_client, unique_email):
        """Test signup with weak password"""
        signup_data = {"email": unique_email, "password": "123"}  # Too short

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 422
        data = response.json()
        assert "code" in data

    def test_signup_missing_email(self, config, http_client):
        """Test signup without email"""
        signup_data = {"password": config.test_password}

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 422

    def test_signup_missing_password(self, config, http_client, unique_email):
        """Test signup without password"""
        signup_data = {"email": unique_email}

        response = http_client.post(f"{config.base_url}/signup", json=signup_data)

        assert response.status_code == 400

    def test_signup_duplicate_email(self, config, http_client, unique_email):
        """Test signup with duplicate email returns faux data"""
        signup_data = {"email": unique_email, "password": config.test_password}

        # First signup
        response1 = http_client.post(f"{config.base_url}/signup", json=signup_data)
        assert response1.status_code in [200, 422, 429]
        user1_data = response1.json()

        # Second signup with same email
        response2 = http_client.post(f"{config.base_url}/signup", json=signup_data)
        assert response2.status_code in [200, 422, 429]
        user2_data = response2.json()

        # Should return faux data (different ID or same structure)
        if response1.status_code == 200 and response2.status_code == 200:
            assert "id" in user2_data
            assert user2_data["email"] == unique_email

        # Cleanup
        cleanup_test_user(config, http_client, user1_data.get("id"))
