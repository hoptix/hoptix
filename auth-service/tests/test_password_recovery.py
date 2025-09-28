import pytest
import requests


class TestPasswordRecovery:
    def test_password_recovery_valid_email(self, config, http_client, unique_email):
        """Test password recovery with valid email"""
        recovery_data = {
            "email": unique_email
        }
        
        response = http_client.post(
            f"{config.base_url}/recover",
            json=recovery_data
        )

        print(response.json())
        
        # Should always return 200 to prevent email enumeration
        assert response.status_code == 200
    
    def test_password_recovery_invalid_email(self, config, http_client):
        """Test password recovery with invalid email format"""
        recovery_data = {
            "email": "invalid-email-format"
        }
        
        response = http_client.post(
            f"{config.base_url}/recover",
            json=recovery_data
        )
        
        # Might return 400 for invalid format or 200 to prevent enumeration
        assert response.status_code in [200, 400]
    
    def test_password_recovery_nonexistent_email(self, config, http_client):
        """Test password recovery with non-existent email"""
        recovery_data = {
            "email": "nonexistent@example.com"
        }
        
        response = http_client.post(
            f"{config.base_url}/recover",
            json=recovery_data
        )
        
        # Should return 200 to prevent email enumeration
        assert response.status_code == 200
    
    def test_password_recovery_missing_email(self, config, http_client):
        """Test password recovery without email"""
        response = http_client.post(
            f"{config.base_url}/recover",
            json={}
        )
        
        assert response.status_code == 400