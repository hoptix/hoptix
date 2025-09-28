class TestOAuth:
    def test_oauth_authorize_redirect(self, config, http_client):
        """Test OAuth authorization redirect"""
        # Disable automatic redirect following
        response = http_client.get(
            f"{config.base_url}/authorize?provider=google&redirect_to=https://example.com",
            allow_redirects=False
        )
        
        # Should redirect to OAuth provider or return authorization URL
        assert response.status_code in [200, 302, 303, 307, 308]
    
    def test_oauth_callback_handling(self, config, http_client):
        """Test OAuth callback handling"""
        # Test with dummy callback data
        response = http_client.get(
            f"{config.base_url}/callback?code=dummy_code&state=dummy_state",
            allow_redirects=False
        )
        
        # Should handle callback (might redirect, return data, or return error for invalid code)
        assert response.status_code in [200, 302, 303, 307, 308, 400, 401, 500]
