import pytest
import requests


class TestErrorHandling:
    def test_unauthorized_requests(self, config, http_client):
        """Test that protected endpoints return 401 without auth"""
        protected_endpoints = [
            ("GET", "/user"),
            ("POST", "/logout"),
            ("GET", "/reauthenticate")
        ]
        
        for method, endpoint in protected_endpoints:
            if method == "GET":
                response = http_client.get(f"{config.base_url}{endpoint}")
            elif method == "POST":
                response = http_client.post(f"{config.base_url}{endpoint}")
            elif method == "PUT":
                response = http_client.put(f"{config.base_url}{endpoint}")
            
            assert response.status_code == 401, f"Endpoint {method} {endpoint} should require auth"
    
    def test_invalid_json_requests(self, config, http_client):
        """Test endpoints with invalid JSON"""
        endpoints = [
            "/signup",
            "/recover",
            "/magiclink",
            "/otp"
        ]
        
        for endpoint in endpoints:
            response = http_client.post(
                f"{config.base_url}{endpoint}",
                data="invalid json",
                headers={"Content-Type": "application/json"}
            )
            assert response.status_code == 400, f"Endpoint {endpoint} should reject invalid JSON"
    
    def test_method_not_allowed(self, config, http_client):
        """Test endpoints with wrong HTTP methods"""
        # Test GET on POST-only endpoints
        post_only_endpoints = ["/signup", "/recover", "/magiclink"]
        
        for endpoint in post_only_endpoints:
            response = http_client.get(f"{config.base_url}{endpoint}")
            # Should return 405 Method Not Allowed or 404
            assert response.status_code in [404, 405]
    
    def test_missing_required_fields(self, config, http_client):
        """Test endpoints with missing required fields"""
        test_cases = [
            ("/signup", {}),
            ("/recover", {}),
            ("/magiclink", {}),
        ]
        
        for endpoint, data in test_cases:
            response = http_client.post(
                f"{config.base_url}{endpoint}",
                json=data
            )

            assert response.status_code in [400, 422]

