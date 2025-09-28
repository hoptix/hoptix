import pytest
import requests


class TestSettings:
    def test_get_settings_success(self, config, http_client):
        """Test that settings endpoint returns expected data"""
        response = http_client.get(f"{config.base_url}/settings")
        
        assert response.status_code == 200
        data = response.json()
        print(data)
        
        # Verify expected fields are present
        assert "external" in data
        assert "disable_signup" in data
        assert isinstance(data["external"], dict)
        assert isinstance(data["disable_signup"], bool)
    
    def test_settings_contains_oauth_providers(self, config, http_client):
        """Test that settings include OAuth provider information"""
        response = http_client.get(f"{config.base_url}/settings")
        
        assert response.status_code == 200
        data = response.json()
        
        external = data.get("external", {})
        # Check for common OAuth providers
        expected_providers = ["google", "github", "facebook"]
        for provider in expected_providers:
            assert provider in external

