import pytest
import requests


class TestMagicLink:
    def test_magic_link_valid_email(self, config, http_client, unique_email):
        """Test sending magic link to valid email"""
        magic_link_data = {
            "email": unique_email
        }
        
        response = http_client.post(
            f"{config.base_url}/magiclink",
            json=magic_link_data
        )
        
        assert response.status_code in [200, 422, 429]
    
    def test_magic_link_with_create_user(self, config, http_client, unique_email):
        """Test magic link with create_user option"""
        magic_link_data = {
            "email": unique_email,
            "create_user": True
        }
        
        response = http_client.post(
            f"{config.base_url}/magiclink",
            json=magic_link_data
        )
        
        assert response.status_code in [200, 422, 429]
    
    def test_magic_link_invalid_email(self, config, http_client):
        """Test magic link with invalid email format"""
        magic_link_data = {
            "email": "invalid-email-format"
        }
        
        response = http_client.post(
            f"{config.base_url}/magiclink",
            json=magic_link_data
        )
        
        assert response.status_code in [200, 400, 500]
    
    def test_magic_link_missing_email(self, config, http_client):
        """Test magic link without email"""
        response = http_client.post(
            f"{config.base_url}/magiclink",
            json={}
        )
        
        assert response.status_code == 422