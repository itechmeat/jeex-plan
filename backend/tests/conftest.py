"""
Pytest configuration and shared fixtures.
"""

import asyncio
import os

# Set required environment variables before app import
os.environ.setdefault("VAULT_TOKEN", "test-token")
os.environ.setdefault("USE_VAULT", "false")
# NOTE: Keep ENVIRONMENT as development for tests to avoid breaking password hashing
# CSRF protection is handled by middleware bypass for stateless API requests

import uuid
from collections.abc import AsyncGenerator

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
    """
    Register custom UUID function for SQLite testing.

    Note: Named 'uuidv7' to match PostgreSQL 18 built-in function used in production,
    but implements uuid4() as a test fallback since SQLite lacks native UUID support.
    This ensures test schema compatibility without requiring actual UUIDv7 implementation.
    """
    import uuid

    # Only register custom functions for SQLite (not for async PostgreSQL)
    if hasattr(dbapi_connection, "create_function"):

        def uuidv7():
            """Test fallback: generates UUIDv4 for SQLite compatibility."""
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
async def test_session(test_db) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session with automatic cleanup."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            # Ensure all pending operations are handled
            try:
                if session.in_transaction():
                    await session.rollback()
            except Exception as exc:
                # Session might already be closed, log for debugging
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    "Session rollback failed during cleanup (session may be closed): %s",
                    exc,
                    exc_info=True,
                )

            # Clean up all data after each test to ensure isolation
            try:
                # Delete all data from all tables to ensure clean state
                for table in reversed(Base.metadata.sorted_tables):
                    await session.execute(table.delete())
                await session.commit()
            except Exception as cleanup_exc:
                # If cleanup fails, try to rollback
                import logging

                logger = logging.getLogger(__name__)
                logger.error(
                    "Data cleanup failed, attempting rollback: %s",
                    cleanup_exc,
                    exc_info=True,
                )
                try:
                    await session.rollback()
                except Exception as rollback_exc:
                    # Session might be in invalid state - this is critical
                    logger.error(
                        "CRITICAL: Session cleanup and rollback both failed: %s",
                        rollback_exc,
                        exc_info=True,
                    )
                    # Re-raise to fail the test and prevent cascading failures
                    pytest.fail(
                        f"Test cleanup failed: {cleanup_exc}. "
                        f"Rollback also failed: {rollback_exc}. "
                        "This may cause subsequent test failures."
                    )


@pytest.fixture
async def async_db(test_session):
    """Backward-compatible alias for async DB session."""
    return test_session


@pytest.fixture
def test_app():
    """Create test FastAPI app instance."""
    return app


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
    # Create user and get token with unique email
    unique_suffix = uuid.uuid4().hex[:8]
    response = test_client.post(
        "/api/v1/auth/register",
        json={
            "email": f"auth-{unique_suffix}@test.com",
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


# Semaphore for controlling concurrent database operations in tests
@pytest.fixture(scope="session")
def db_semaphore():
    """Semaphore to limit concurrent database operations in tests."""
    return asyncio.Semaphore(5)  # Allow max 5 concurrent DB operations


@pytest.fixture
async def async_client(test_session):
    """Create async test client with database override"""

    async def override_get_db():
        # Create a new session for each request to avoid sharing state
        async with TestSessionLocal() as session:
            try:
                yield session
            finally:
                try:
                    if session.in_transaction():
                        await session.rollback()
                except Exception:
                    pass

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
        description="Test tenant for testing",
        is_active=True,
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest.fixture
async def test_user(test_session, test_tenant):
    """Create a test user"""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"test-{unique_suffix}@example.com",
        username=f"testuser-{unique_suffix}",
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
        description="Second test tenant for testing",
        is_active=True,
    )
    test_session.add(tenant)
    await test_session.commit()
    await test_session.refresh(tenant)
    return tenant


@pytest.fixture
async def second_user(test_session, second_tenant):
    """Create a test user in second tenant"""
    unique_suffix = uuid.uuid4().hex[:8]
    user = User(
        id=uuid.uuid4(),
        email=f"second-{unique_suffix}@example.com",
        username=f"seconduser-{unique_suffix}",
        hashed_password="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj3vCWmTB5Va",  # hashed "test123456"
        full_name="Second User",
        tenant_id=second_tenant.id,
        is_active=True,
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
    async def create_tenant(name=None, slug=None, **kwargs):
        unique_suffix = uuid.uuid4().hex[:8]
        if name is None:
            name = f"Test Tenant {unique_suffix}"
        if slug is None:
            slug = f"{name.lower().replace(' ', '-')}-{unique_suffix}"
        tenant_repo = TenantRepository(test_session)
        return await tenant_repo.create_tenant(name=name, slug=slug, **kwargs)

    async def create_user(
        tenant_id,
        email=None,
        username=None,
        password="test123456",
        **kwargs,
    ):
        unique_suffix = uuid.uuid4().hex[:8]
        if email is None:
            email = f"test-{unique_suffix}@example.com"
        if username is None:
            username = f"testuser-{unique_suffix}"

        user_service = UserService(test_session, tenant_id)
        result = await user_service.register_user(
            email=email,
            username=username,
            password=password,
            full_name=kwargs.get("full_name", username.title()),
            tenant_id=tenant_id,
        )
        # Extract user from registration result
        return result["user"]

    # Add methods to session
    test_session.create_tenant = create_tenant
    test_session.create_user = create_user

    return test_session


@pytest.fixture
async def db_session(test_db_session):
    """Alias for test_db_session to match test expectations"""
    return test_db_session


@pytest.fixture
async def tenant_setup(test_session):
    """Create complete tenant setup with two tenants and users for multi-tenant testing"""
    from app.repositories.tenant import TenantRepository
    from app.repositories.user import UserRepository
    from app.services.user import UserService

    tenant_repo = TenantRepository(test_session)

    # Create tenant A
    unique_suffix_a = uuid.uuid4().hex[:8]
    tenant_a = await tenant_repo.create_tenant(
        name=f"Tenant A {unique_suffix_a}",
        slug=f"tenant-a-{unique_suffix_a}",
        description="First test tenant for multi-tenant testing",
    )

    # Create tenant B
    unique_suffix_b = uuid.uuid4().hex[:8]
    tenant_b = await tenant_repo.create_tenant(
        name=f"Tenant B {unique_suffix_b}",
        slug=f"tenant-b-{unique_suffix_b}",
        description="Second test tenant for multi-tenant testing",
    )

    # Create user A in tenant A
    user_service_a = UserService(test_session, tenant_a.id)
    user_a_data = await user_service_a.register_user(
        email=f"user-a-{unique_suffix_a}@tenant-a.com",
        username=f"user_a_{unique_suffix_a}",
        password="TenantTestPassword123!",
        full_name="User A",
        tenant_id=tenant_a.id,
    )
    # Get user object from repository
    user_repo_a = UserRepository(test_session, tenant_a.id)
    user_a = await user_repo_a.get_by_id(uuid.UUID(user_a_data["user"]["id"]))

    # Create user B in tenant B
    user_service_b = UserService(test_session, tenant_b.id)
    user_b_data = await user_service_b.register_user(
        email=f"user-b-{unique_suffix_b}@tenant-b.com",
        username=f"user_b_{unique_suffix_b}",
        password="TenantTestPassword456!",
        full_name="User B",
        tenant_id=tenant_b.id,
    )
    # Get user object from repository
    user_repo_b = UserRepository(test_session, tenant_b.id)
    user_b = await user_repo_b.get_by_id(uuid.UUID(user_b_data["user"]["id"]))

    # Create additional user in tenant A for cross-tenant testing
    user_a2_data = await user_service_a.register_user(
        email=f"user-a2-{unique_suffix_a}@tenant-a.com",
        username=f"user_a2_{unique_suffix_a}",
        password="TenantTestPassword789!",
        full_name="User A2",
        tenant_id=tenant_a.id,
    )
    # Get user object from repository
    user_a2 = await user_repo_a.get_by_id(uuid.UUID(user_a2_data["user"]["id"]))

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "user_a": user_a,
        "user_b": user_b,
        "user_a2": user_a2,
        "tokens_a": user_a_data["tokens"],
        "tokens_b": user_b_data["tokens"],
        "tokens_a2": user_a2_data["tokens"],
    }


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


@pytest.fixture
def mock_password_service():
    """
    Mock password service for testing that bypasses password validation.

    Use this fixture to create UserService instances in tests that need
    weak passwords without exposing skip_password_validation in production code.

    Example:
        user_service = UserService(db_session, tenant_id)
        user_service.password_service = mock_password_service
        user = await user_service.create_user(email="test@example.com", password="weak")
    """
    from passlib.context import CryptContext
    from app.core.password_service import PasswordService

    # Create real password service but override validation
    service = PasswordService()

    # Bypass validation by replacing with no-op
    service._validate_password_strength = lambda password: None

    return service


@pytest.fixture(autouse=True)
def mock_openai_embeddings(monkeypatch):
    """
    Auto-mock OpenAI API calls for all tests to avoid authentication errors.
    Returns deterministic embeddings for testing purposes.
    """
    import numpy as np
    from unittest.mock import AsyncMock, MagicMock

    async def mock_create_embedding(*args, **kwargs):
        """Generate mock embeddings with balanced semantic similarity."""
        input_data = kwargs.get("input", [])
        if isinstance(input_data, str):
            input_data = [input_data]

        # Generate semantic-aware embeddings
        embeddings = []
        for text in input_data:
            # Extract meaningful words (filter stop words)
            stop_words = {
                "a",
                "an",
                "the",
                "and",
                "or",
                "but",
                "is",
                "are",
                "was",
                "were",
                "to",
                "of",
                "in",
                "on",
                "at",
                "by",
                "for",
                "with",
            }
            words = [
                w.lower() for w in text.lower().split() if w.lower() not in stop_words
            ]

            # Start with moderate random base for baseline similarity
            text_hash = hash(text) % 10000
            np.random.seed(text_hash)
            vector = np.random.rand(1536) * 0.5  # Moderate base for threshold passing

            # Add word-based components with higher weight
            for word in words:
                # Map each word to multiple dimensions for better overlap
                word_seed = hash(word) % 10000
                np.random.seed(word_seed)

                # Primary dimension for this word
                primary_dim = hash(word) % 1536
                vector[primary_dim] += 3.0  # Strong signal

                # Secondary dimensions for semantic clustering (more spread)
                for i in range(8):
                    secondary_dim = (hash(word + str(i))) % 1536
                    vector[secondary_dim] += 0.8

            # Normalize to unit length for cosine similarity
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm

            embeddings.append(vector.tolist())

        # Mock OpenAI response structure
        mock_response = MagicMock()
        mock_response.data = [MagicMock(embedding=emb) for emb in embeddings]
        return mock_response

    # Patch the OpenAI client's create method
    mock_client = AsyncMock()
    mock_client.with_options = lambda **kwargs: mock_client
    mock_client.embeddings = AsyncMock()
    mock_client.embeddings.create = AsyncMock(side_effect=mock_create_embedding)

    # Patch at openai module level (where it's imported from)
    monkeypatch.setattr("openai.AsyncOpenAI", lambda **kwargs: mock_client)


@pytest.fixture(autouse=True)
def bypass_password_validation_globally(monkeypatch):
    """
    Auto-bypass password strength validation for all tests.
    This allows using simple test passwords like 'password123' without errors.
    """
    from app.core.password_service import PasswordService

    # Patch the validation method to do nothing
    monkeypatch.setattr(
        PasswordService, "_validate_password_strength", lambda self, password: None
    )
