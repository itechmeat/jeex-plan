"""
Pytest configuration and shared fixtures.
"""

import os

# Set required environment variables before app import
os.environ.setdefault("VAULT_TOKEN", "test-token")
os.environ.setdefault("USE_VAULT", "false")
os.environ.setdefault("ENVIRONMENT", "testing")

import uuid

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models import Base
from app.models.tenant import Tenant
from app.models.user import User

# Test database setup
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Create custom event listeners for SQLite UUID generation


@event.listens_for(Engine, "connect")
def sqlite_connect(dbapi_connection, connection_record):
    # Register custom UUID function for SQLite
    import uuid

    def uuidv7():
        return str(uuid.uuid4())

    dbapi_connection.create_function("uuidv7", 0, uuidv7)


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
    # Disable rate limiting for tests
    settings.RATE_LIMIT_REQUESTS = 10000
    settings.RATE_LIMIT_WINDOW = 1

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


@pytest.fixture
async def async_client(test_session):
    """Create async test client with database override"""

    def override_get_db():
        yield test_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def test_tenant(test_session):
    """Create a test tenant with unique slug"""
    unique_suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Test Tenant {unique_suffix}",
        slug=f"test-tenant-{unique_suffix}",
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(test_session, test_tenant):
    """Create a test user"""
    user = User(
        id=uuid.uuid4(),
        email="test@example.com",
        username="testuser",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3vCWmTB5Va",  # hashed "test123456"
        full_name="Test User",
        tenant_id=test_tenant.id,
        is_active=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def second_tenant(test_session):
    """Create a second test tenant for multi-tenant testing"""
    unique_suffix = uuid.uuid4().hex[:8]
    tenant = Tenant(
        id=uuid.uuid4(),
        name=f"Second Tenant {unique_suffix}",
        slug=f"second-tenant-{unique_suffix}",
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest.fixture
async def second_user(test_session, second_tenant):
    """Create a test user in second tenant"""
    user = User(
        id=uuid.uuid4(),
        email="second@example.com",
        username="seconduser",
        password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3vCWmTB5Va",  # hashed "test123456"
        full_name="Second User",
        tenant_id=second_tenant.id,
        is_active=True,
        is_verified=True,
    )
    test_session.add(user)
    await test_session.commit()
    await test_session.refresh(user)
    return user


@pytest.fixture
async def user_service(test_session, test_tenant):
    """Create a UserService instance for testing"""
    from app.services.user import UserService

    return UserService(test_session, test_tenant.id)


@pytest.fixture
async def tenant_repository(test_session):
    """Create a TenantRepository instance for testing"""
    from app.repositories.tenant import TenantRepository

    return TenantRepository(test_session)


@pytest.fixture
async def user_repository(test_session, test_tenant):
    """Create a UserRepository instance for testing"""
    from app.repositories.user import UserRepository

    return UserRepository(test_session, test_tenant.id)


# Add helper methods to TestDBSession class
@pytest.fixture
async def test_db_session(test_session):
    """Enhanced test session with helper methods"""
    from app.repositories.tenant import TenantRepository
    from app.services.user import UserService

    # Add helper methods to the session
    async def create_tenant(name="Test Tenant", slug=None, **kwargs):
        if slug is None:
            slug = f"{name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}"
        tenant_repo = TenantRepository(test_session)
        return await tenant_repo.create_tenant(name=name, slug=slug, **kwargs)

    async def create_user(
        tenant_id,
        email="test@example.com",
        username=None,
        password="test123456",
        **kwargs,
    ):
        if username is None:
            username = email.split("@")[0]

        user_service = UserService(test_session, tenant_id)
        return await user_service.create_user(
            email=email,
            username=username,
            password=password,
            full_name=kwargs.get("full_name", username.title()),
            is_active=kwargs.get("is_active", True),
            is_verified=kwargs.get("is_verified", True),
        )

    # Add methods to session
    test_session.create_tenant = create_tenant
    test_session.create_user = create_user

    return test_session


@pytest.fixture
async def db_session(test_db_session):
    """Alias for test_db_session to match test expectations"""
    return test_db_session


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
