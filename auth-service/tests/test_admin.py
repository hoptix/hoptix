import pytest


def cleanup_test_user(config, http_client, user_id):
    """Helper to clean up test users"""
    if not user_id or not config.service_role_key:
        return

    try:
        headers = {"Authorization": f"Bearer {config.service_role_key}"}
        http_client.delete(f"{config.base_url}/admin/users/{user_id}", headers=headers)
    except Exception:
        pass  # Ignore cleanup errors


class TestAdmin:
    def test_admin_create_user(self, config, http_client, unique_email):
        """Test creating user via admin endpoint"""
        if not config.service_role_key:
            pytest.skip("Service role key not provided")

        headers = {"Authorization": f"Bearer {config.service_role_key}"}

        user_data = {
            "email": unique_email,
            "password": config.test_password,
            "email_confirm": True,
            "user_metadata": {"created_by": "admin_test"},
        }

        response = http_client.post(
            f"{config.base_url}/admin/users", json=user_data, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["email"] == unique_email
        assert "id" in data

        # Cleanup
        cleanup_test_user(config, http_client, data["id"])

    def test_admin_generate_link(self, config, http_client):
        """Test generating action link"""
        if not config.service_role_key:
            pytest.skip("Service role key not provided")

        headers = {"Authorization": f"Bearer {config.service_role_key}"}

        link_data = {"type": "invite", "email": config.test_email}

        response = http_client.post(
            f"{config.base_url}/admin/generate_link", json=link_data, headers=headers
        )

        assert response.status_code in [200, 422, 429]
        data = response.json()

        if response.status_code == 200:
            assert "action_link" in data

    def test_admin_invite_user(self, config, http_client, unique_email):
        """Test inviting a user"""
        if not config.service_role_key:
            pytest.skip("Service role key not provided")

        headers = {"Authorization": f"Bearer {config.service_role_key}"}

        invite_data = {"email": unique_email, "data": {"role": "invited_user"}}

        response = http_client.post(
            f"{config.base_url}/invite", json=invite_data, headers=headers
        )
        print(response.json())
        assert response.status_code in [200, 422, 429]

    def test_admin_unauthorized(self, config, http_client, unique_email):
        """Test admin endpoints without proper authorization"""
        user_data = {"email": unique_email, "password": config.test_password}

        response = http_client.post(f"{config.base_url}/admin/users", json=user_data)

        assert response.status_code == 401
