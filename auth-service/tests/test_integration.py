import pytest
import requests
import time


def cleanup_test_user(config, http_client, user_id):
    """Helper to clean up test users"""
    if not user_id or not config.service_role_key:
        return

    try:
        headers = {"Authorization": f"Bearer {config.service_role_key}"}
        http_client.delete(f"{config.base_url}/admin/users/{user_id}", headers=headers)
    except Exception:
        pass  # Ignore cleanup errors


class TestIntegration:
    def test_complete_auth_flow(self, config, http_client):
        """Test complete authentication flow"""
        if not config.service_role_key:
            pytest.skip("Service role key not provided")

        timestamp = int(time.time())
        flow_email = f"flow-test-{timestamp}@gmail.com"

        # Use admin API to create a pre-confirmed user
        admin_headers = {"Authorization": f"Bearer {config.service_role_key}"}

        # 1. Create confirmed user via admin API
        signup_data = {
            "email": flow_email,
            "password": config.test_password,
            "email_confirm": True,
            "user_metadata": {"integration_test": True},
        }

        signup_response = http_client.post(
            f"{config.base_url}/admin/users", json=signup_data, headers=admin_headers
        )

        assert signup_response.status_code == 200

        user_data = signup_response.json()
        user_id = user_data["id"]

        try:
            # 2. Login with the confirmed user
            login_data = {"email": flow_email, "password": config.test_password}

            login_response = http_client.post(
                f"{config.base_url}/token?grant_type=password", json=login_data
            )

            assert login_response.status_code == 200
            auth_data = login_response.json()
            access_token = auth_data["access_token"]

            headers = {"Authorization": f"Bearer {access_token}"}

            # 3. Get user profile
            profile_response = http_client.get(
                f"{config.base_url}/user", headers=headers
            )
            assert profile_response.status_code == 200

            profile_data = profile_response.json()
            assert profile_data["email"] == flow_email

            # 4. Update user metadata
            update_data = {
                "data": {"flow_completed": True, "test_timestamp": timestamp}
            }

            update_response = http_client.put(
                f"{config.base_url}/user", json=update_data, headers=headers
            )
            # Accept both success and reauthentication required
            assert update_response.status_code in [200, 400]

            # 5. Test refresh token
            if "refresh_token" in auth_data:
                refresh_data = {"refresh_token": auth_data["refresh_token"]}

                refresh_response = http_client.post(
                    f"{config.base_url}/token?grant_type=refresh_token",
                    json=refresh_data,
                )
                assert refresh_response.status_code == 200

            # 6. Logout
            logout_response = http_client.post(
                f"{config.base_url}/logout", headers=headers
            )
            assert logout_response.status_code == 204

        finally:
            # Cleanup
            cleanup_test_user(config, http_client, user_id)

    def test_admin_user_lifecycle(self, config, http_client):
        """Test admin user management lifecycle"""
        if not config.service_role_key:
            pytest.skip("Service role key not provided")

        timestamp = int(time.time())
        admin_email = f"admin-lifecycle-{timestamp}@example.com"

        headers = {"Authorization": f"Bearer {config.service_role_key}"}

        # 1. Create user via admin
        create_data = {
            "email": admin_email,
            "password": config.test_password,
            "email_confirm": True,
            "user_metadata": {"created_via": "admin_test", "test_id": timestamp},
        }

        create_response = http_client.post(
            f"{config.base_url}/admin/users", json=create_data, headers=headers
        )
        assert create_response.status_code == 200

        user_data = create_response.json()
        user_id = user_data["id"]

        try:
            # 2. Generate action link for user
            link_data = {"type": "recovery", "email": admin_email}

            link_response = http_client.post(
                f"{config.base_url}/admin/generate_link",
                json=link_data,
                headers=headers,
            )
            assert link_response.status_code == 200

            link_data = link_response.json()
            assert "action_link" in link_data

            # 3. Update user via admin
            update_data = {
                "user_metadata": {
                    "updated_via": "admin_test",
                    "update_timestamp": timestamp,
                }
            }

            update_response = http_client.put(
                f"{config.base_url}/admin/users/{user_id}",
                json=update_data,
                headers=headers,
            )
            assert update_response.status_code == 200

        finally:
            # Cleanup
            cleanup_test_user(config, http_client, user_id)
