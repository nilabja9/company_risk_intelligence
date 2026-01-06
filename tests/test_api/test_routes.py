import pytest


class TestHealthEndpoint:
    def test_health_check(self, test_client):
        """Test the health check endpoint."""
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestRootEndpoint:
    def test_root(self, test_client):
        """Test the root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data


class TestAPIInfoEndpoint:
    def test_api_info(self, test_client):
        """Test the API info endpoint."""
        response = test_client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "target_companies" in data
