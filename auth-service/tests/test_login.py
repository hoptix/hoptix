# tests/test_login.py

from unittest.mock import patch, MagicMock, PropertyMock


def test_login_success(client):
    mock_user = MagicMock()
    type(mock_user).id = PropertyMock(return_value="user-123")
    type(mock_user).email = PropertyMock(return_value="user@example.com")

    mock_session = MagicMock()
    type(mock_session).access_token = PropertyMock(return_value="fake-token")

    with patch("routes.auth.supabase.auth.sign_in_with_password") as mock_login:
        mock_login.return_value = MagicMock(user=mock_user, session=mock_session)

        response = client.post(
            "/auth/login",
            json={"email": "user@example.com", "password": "StrongPass123!"},
        )

        assert response.status_code == 200
        assert response.json["access_token"] == "fake-token"
        assert response.json["user"]["email"] == "user@example.com"


def test_login_failure(client):
    with patch("routes.auth.supabase.auth.sign_in_with_password") as mock_login:
        mock_login.return_value = MagicMock(user=None, session=None)

        response = client.post(
            "/auth/login", json={"email": "fail@example.com", "password": "wrongpass"}
        )

        assert response.status_code == 400
