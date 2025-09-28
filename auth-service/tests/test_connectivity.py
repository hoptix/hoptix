import pytest
import requests


class TestConnectivity:
    def test_service_is_reachable(self, config, http_client):
        """Test that the service is running and reachable"""
        try:
            response = http_client.get(f"{config.base_url}/settings", timeout=10)
            assert response.status_code < 500, "Service should be reachable"
        except requests.exceptions.ConnectionError:
            pytest.fail("Cannot connect to the service. Is it running?")
        except requests.exceptions.Timeout:
            pytest.fail("Service is not responding within timeout")
    
    def test_supabase_connectivity(self, config, http_client):
        """Test connectivity to Supabase"""
        # Test via our service's settings endpoint which calls Supabase
        response = http_client.get(f"{config.base_url}/settings")
        
        # If our service can reach Supabase, this should work
        assert response.status_code == 200, "Cannot reach Supabase through our service"
    
    def test_health_check_via_settings(self, config, http_client):
        """Use settings endpoint as a health check"""
        response = http_client.get(f"{config.base_url}/settings")
        
        assert response.status_code == 200
        data = response.json()
        
        # Basic validation that we got a proper response from Supabase
        assert isinstance(data, dict)
        assert len(data) > 0