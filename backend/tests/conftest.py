"""
Pytest configuration and shared fixtures.
"""

import os

# Set required environment variables before app import
os.environ.setdefault("VAULT_TOKEN", "test-token")
os.environ.setdefault("USE_VAULT", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

TestSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
async def test_db():
    """Create test database"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_session(test_db):
    """Create test database session"""
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture
async def async_db(test_session):
    """Backward-compatible alias for async DB session."""
    return test_session


@pytest.fixture
def test_client(test_session):
    """Create test client with test database"""

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def mock_settings():
    """Mock settings for testing"""
    original_settings = settings.copy()
    settings.ENVIRONMENT = "testing"
    settings.DEBUG = True
    settings.DATABASE_URL = TEST_DATABASE_URL

    yield

    # Restore original settings
    for key, value in original_settings.items():
        setattr(settings, key, value)


@pytest.fixture
def sample_project_data():
    """Sample project data for testing"""
    return {"name": "Test Project", "language": "en"}


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpassword123",
        "confirm_password": "testpassword123",
    }


@pytest.fixture
def auth_headers(test_client):
    """Get authentication headers for testing"""
    # Create user and get token
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": "auth@test.com",
            "name": "Auth User",
            "password": "authpassword123",
            "confirm_password": "authpassword123",
        },
    )

    if response.status_code == 200:
        token = response.json()["token"]["access_token"]
        return {"Authorization": f"Bearer {token}"}

    return {}


# Async test client fixture
@pytest.fixture
async def async_test_client():
    """Create async test client"""
    from app.main import app

    async with TestClient(app) as client:
        yield client


# Pytest configuration
def pytest_configure(config) -> None:
    """Configure pytest"""
    config.addinivalue_line("markers", "asyncio: mark test as async")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")


def pytest_collection_modifyitems(config, items) -> None:
    """Modify test collection to add markers"""
    for item in items:
        # Mark async tests
        if any(name in item.name for name in ["test_async", "test_"]):
            item.add_marker(pytest.mark.asyncio)

        # Mark integration tests
        if "integration" in item.name:
            item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if "slow" in item.name:
            item.add_marker(pytest.mark.slow)
