import pytest
import requests


class TestResend:
    def test_resend_signup_confirmation(self, config, http_client):
        """Test resending signup confirmation"""
        resend_data = {
            "email": config.test_email,
            "type": "signup"
        }
        
        response = http_client.post(
            f"{config.base_url}/resend",
            json=resend_data
        )
        
        assert response.status_code in [200, 422, 429]
    
    def test_resend_sms_confirmation(self, config, http_client):
        """Test resending SMS confirmation"""
        resend_data = {
            "phone": config.test_phone,
            "type": "sms"
        }
        
        response = http_client.post(
            f"{config.base_url}/resend",
            json=resend_data
        )
        
        # SMS might not be configured
        assert response.status_code in [200, 400]
    
    def test_resend_invalid_type(self, config, http_client):
        """Test resend with invalid type"""
        resend_data = {
            "email": config.test_email,
            "type": "invalid_type"
        }
        
        response = http_client.post(
            f"{config.base_url}/resend",
            json=resend_data
        )
        
        assert response.status_code == 400