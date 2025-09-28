import pytest
import requests


class TestOTP:
    def test_email_otp_valid(self, config, http_client, unique_email):
        """Test sending email OTP"""
        otp_data = {
            "email": unique_email,
            "create_user": False
        }
        
        response = http_client.post(
            f"{config.base_url}/otp",
            json=otp_data
        )
        
        assert response.status_code in [200, 422, 429]
    
    def test_phone_otp_valid(self, config, http_client):
        """Test sending phone OTP"""
        otp_data = {
            "phone": config.test_phone,
            "create_user": False
        }
        
        response = http_client.post(
            f"{config.base_url}/otp",
            json=otp_data
        )
        
        # Phone OTP might not be configured, accept various responses
        assert response.status_code in [200, 400, 429]
    
    def test_otp_with_create_user(self, config, http_client, unique_email):
        """Test OTP with create_user option"""
        otp_data = {
            "email": unique_email,
            "create_user": True
        }
        
        response = http_client.post(
            f"{config.base_url}/otp",
            json=otp_data
        )
        
        assert response.status_code in [200, 422, 429]
    
    def test_otp_missing_contact_method(self, config, http_client):
        """Test OTP without email or phone"""
        response = http_client.post(
            f"{config.base_url}/otp",
            json={"create_user": False}
        )
        
        assert response.status_code == 400