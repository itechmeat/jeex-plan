"""
Health check endpoint tests.
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestHealthEndpoints:
    """Test health check endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_root_endpoint(self, client) -> None:
        """Test root endpoint returns basic info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "environment" in data
        assert data["service"] == "JEEX Plan API"

    def test_simple_health_check(self, client) -> None:
        """Test simple health check endpoint"""
        response = client.get("/api/v1/health/simple")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    @patch("app.api.routes.health.DatabaseManager.health_check")
    @patch("app.api.routes.health.RedisAdapter")
    @patch("app.api.routes.health.QdrantAdapter")
    def test_comprehensive_health_check_healthy(
        self, mock_qdrant_adapter, mock_redis_adapter, mock_db_health_check, client
    ) -> None:
        """Test comprehensive health check when all services are healthy"""
        # Mock healthy responses
        mock_db_health_check.return_value = {
            "status": "healthy",
            "message": "Database connection successful",
            "details": {},
        }

        mock_redis_instance = AsyncMock()
        mock_redis_instance.health_check.return_value = {
            "status": "healthy",
            "message": "Redis connection successful",
            "details": {},
        }
        mock_redis_adapter.return_value = mock_redis_instance

        mock_qdrant_instance = AsyncMock()
        mock_qdrant_instance.health_check.return_value = {
            "status": "healthy",
            "message": "Qdrant connection successful",
            "details": {},
        }
        mock_qdrant_adapter.return_value = mock_qdrant_instance

        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["redis"]["status"] == "healthy"
        assert data["components"]["qdrant"]["status"] == "healthy"

    @patch("app.api.routes.health.DatabaseManager.health_check")
    def test_comprehensive_health_check_unhealthy_database(
        self, mock_db_health_check, client
    ) -> None:
        """Test comprehensive health check when database is unhealthy"""
        # Mock unhealthy database response
        mock_db_health_check.return_value = {
            "status": "unhealthy",
            "message": "Database connection failed",
            "details": {"error": "Connection timeout"},
        }

        response = client.get("/api/v1/health")
        assert response.status_code == 503
        data = response.json()
        assert data["detail"]["error"] == "Service unavailable"
        assert "database" in data["detail"]["unhealthy_components"]

    def test_readiness_check(self, client) -> None:
        """Test readiness check endpoint"""
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"

    def test_liveness_check(self, client) -> None:
        """Test liveness check endpoint"""
        response = client.get("/api/v1/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_metrics(self, client) -> None:
        """Test health metrics endpoint"""
        response = client.get("/api/v1/health/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "components" in data
        assert "features" in data
