"""
Test models for Epic 01 - Multi-tenant foundation.
"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.document import Document, DocumentStatus, DocumentType
from app.models.project import Project, ProjectStatus
from app.models.tenant import Tenant
from app.models.user import User


class TestTenantModel:
    """Test Tenant model functionality."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, test_session) -> None:
        """Test creating a tenant."""
        tenant = Tenant(
            name="Test Company",
            slug="test-company",
            description="A test company",
            is_active=True,
        )

        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        assert tenant.id is not None
        assert tenant.name == "Test Company"
        assert tenant.slug == "test-company"
        assert tenant.is_active is True
        assert tenant.created_at is not None
        assert tenant.updated_at is not None

    @pytest.mark.asyncio
    async def test_tenant_slug_unique(self, test_session) -> None:
        """Test that tenant slugs must be unique."""
        tenant1 = Tenant(name="Company 1", slug="unique-slug")
        tenant2 = Tenant(name="Company 2", slug="unique-slug")

        test_session.add(tenant1)
        test_session.add(tenant2)

        with pytest.raises(IntegrityError):
            await test_session.commit()


class TestUserModel:
    """Test User model functionality."""

    @pytest.fixture
    async def sample_tenant(self, test_session):
        """Create a sample tenant for testing."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for models testing",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)
        return tenant

    @pytest.mark.asyncio
    async def test_create_user(self, test_session, sample_tenant) -> None:
        """Test creating a user."""
        unique_suffix = uuid.uuid4().hex[:8]
        user = User(
            tenant_id=sample_tenant.id,
            email=f"test-{unique_suffix}@example.com",
            username=f"testuser-{unique_suffix}",
            full_name="Test User",
            is_active=True,
            is_superuser=False,
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.id is not None
        assert user.tenant_id == sample_tenant.id
        assert user.email == f"test-{unique_suffix}@example.com"
        assert user.username == f"testuser-{unique_suffix}"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_deleted is False

    @pytest.mark.asyncio
    async def test_user_oauth_fields(self, test_session, sample_tenant) -> None:
        """Test user OAuth fields."""
        unique_suffix = uuid.uuid4().hex[:8]
        user = User(
            tenant_id=sample_tenant.id,
            email=f"oauth-{unique_suffix}@example.com",
            username=f"oauthuser-{unique_suffix}",
            oauth_provider="google",
            oauth_id="google_123456",
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_123456"

    @pytest.mark.asyncio
    async def test_user_tenant_email_unique(self, test_session, sample_tenant) -> None:
        """Test that email is unique within a tenant."""
        unique_suffix = uuid.uuid4().hex[:8]
        same_email = f"same-{unique_suffix}@example.com"
        username1 = f"user1-{unique_suffix}"
        username2 = f"user2-{unique_suffix}"
        user1 = User(
            tenant_id=sample_tenant.id,
            email=same_email,
            username=username1,
        )
        user2 = User(
            tenant_id=sample_tenant.id,
            email=same_email,
            username=username2,
        )

        test_session.add(user1)
        test_session.add(user2)

        with pytest.raises(IntegrityError):
            await test_session.commit()


class TestProjectModel:
    """Test Project model functionality."""

    @pytest.fixture
    async def sample_tenant_and_user(self, test_session):
        """Create sample tenant and user for testing."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for project testing",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{unique_suffix}@example.com",
            username=f"owner-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        return tenant, user

    @pytest.mark.asyncio
    async def test_create_project(self, test_session, sample_tenant_and_user) -> None:
        """Test creating a project."""
        tenant, user = sample_tenant_and_user

        project = Project(
            tenant_id=tenant.id,
            name="Test Project",
            description="A test project",
            status=ProjectStatus.DRAFT,
            owner_id=user.id,
        )

        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        assert project.id is not None
        assert project.tenant_id == tenant.id
        assert project.name == "Test Project"
        assert project.status == ProjectStatus.DRAFT
        assert project.owner_id == user.id
        assert project.is_deleted is False

    @pytest.mark.asyncio
    async def test_project_status_enum(
        self, test_session, sample_tenant_and_user
    ) -> None:
        """Test project status enum values."""
        tenant, user = sample_tenant_and_user

        for status in ProjectStatus:
            project = Project(
                tenant_id=tenant.id,
                name=f"Project {status.value}",
                status=status,
                owner_id=user.id,
            )
            test_session.add(project)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_project_tenant_name_unique(
        self, test_session, sample_tenant_and_user
    ) -> None:
        """Test that project names are unique within a tenant."""
        tenant, user = sample_tenant_and_user

        project1 = Project(tenant_id=tenant.id, name="Unique Project", owner_id=user.id)
        project2 = Project(tenant_id=tenant.id, name="Unique Project", owner_id=user.id)

        test_session.add(project1)
        test_session.add(project2)

        with pytest.raises(IntegrityError):
            await test_session.commit()


class TestDocumentModel:
    """Test Document model functionality."""

    @pytest.fixture
    async def sample_project_setup(self, test_session):
        """Create sample tenant, user, and project for testing."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for document testing",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{unique_suffix}@example.com",
            username=f"owner-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name=f"Test Project {unique_suffix}",
            owner_id=user.id,
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        return tenant, user, project

    @pytest.mark.asyncio
    async def test_create_document(self, test_session, sample_project_setup) -> None:
        """Test creating a document."""
        tenant, _user, project = sample_project_setup

        document = Document(
            tenant_id=tenant.id,
            title="Test Document",
            content="This is test content",
            document_type=DocumentType.ARCHITECTURE,
            status=DocumentStatus.PENDING,
            project_id=project.id,
            generation_step=1,
            generation_progress=0,
        )

        test_session.add(document)
        await test_session.commit()
        await test_session.refresh(document)

        assert document.id is not None
        assert document.tenant_id == tenant.id
        assert document.title == "Test Document"
        assert document.document_type == DocumentType.ARCHITECTURE
        assert document.status == DocumentStatus.PENDING
        assert document.project_id == project.id
        assert document.generation_step == 1
        assert document.generation_progress == 0
        assert document.is_deleted is False

    @pytest.mark.asyncio
    async def test_document_type_enum(self, test_session, sample_project_setup) -> None:
        """Test document type enum values."""
        tenant, _user, project = sample_project_setup

        for doc_type in DocumentType:
            document = Document(
                tenant_id=tenant.id,
                title=f"Document {doc_type.value}",
                document_type=doc_type,
                status=DocumentStatus.PENDING,
                project_id=project.id,
            )
            test_session.add(document)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_document_status_enum(
        self, test_session, sample_project_setup
    ) -> None:
        """Test document status enum values."""
        tenant, _user, project = sample_project_setup

        for status in DocumentStatus:
            document = Document(
                tenant_id=tenant.id,
                title=f"Document {status.value}",
                document_type=DocumentType.PLANNING,
                status=status,
                project_id=project.id,
            )
            test_session.add(document)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_document_generation_metadata(
        self, test_session, sample_project_setup
    ) -> None:
        """Test document generation metadata fields."""
        tenant, _user, project = sample_project_setup

        document = Document(
            tenant_id=tenant.id,
            title="Generation Test",
            document_type=DocumentType.TECHNICAL_SPEC,
            status=DocumentStatus.GENERATING,
            project_id=project.id,
            generation_step=3,
            generation_progress=75,
            error_message="Some error occurred",
        )

        test_session.add(document)
        await test_session.commit()
        await test_session.refresh(document)

        assert document.generation_step == 3
        assert document.generation_progress == 75
        assert document.error_message == "Some error occurred"


class TestModelRelationships:
    """Test relationships between models."""

    @pytest.mark.asyncio
    async def test_tenant_user_relationship(self, test_session) -> None:
        """Test tenant-user relationship."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for relationships",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"test-{unique_suffix}@example.com",
            username=f"testuser-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()

        # Test relationship access (this requires eager loading in real scenarios)
        assert user.tenant_id == tenant.id

    @pytest.mark.asyncio
    async def test_user_project_relationship(self, test_session) -> None:
        """Test user-project relationship."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for user-project relationships",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{unique_suffix}@example.com",
            username=f"owner-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name=f"Test Project {unique_suffix}",
            owner_id=user.id,
        )
        test_session.add(project)
        await test_session.commit()

        assert project.owner_id == user.id

    @pytest.mark.asyncio
    async def test_project_document_relationship(self, test_session) -> None:
        """Test project-document relationship."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for project-document relationships",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{unique_suffix}@example.com",
            username=f"owner-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name=f"Test Project {unique_suffix}",
            owner_id=user.id,
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        document = Document(
            tenant_id=tenant.id,
            title=f"Test Document {unique_suffix}",
            document_type=DocumentType.ARCHITECTURE,
            status=DocumentStatus.PENDING,
            project_id=project.id,
        )
        test_session.add(document)
        await test_session.commit()

        assert document.project_id == project.id


class TestSoftDelete:
    """Test soft delete functionality."""

    @pytest.mark.asyncio
    async def test_user_soft_delete(self, test_session) -> None:
        """Test user soft delete functionality."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for soft delete",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"delete-{unique_suffix}@example.com",
            username=f"deleteuser-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Soft delete
        user.is_deleted = True
        user.deleted_at = datetime.now(UTC)
        await test_session.commit()

        assert user.is_deleted is True
        assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_project_soft_delete(self, test_session) -> None:
        """Test project soft delete functionality."""
        unique_suffix = uuid.uuid4().hex[:8]
        tenant = Tenant(
            name=f"Test Tenant {unique_suffix}",
            slug=f"test-tenant-{unique_suffix}",
            description="Test tenant for project soft delete",
            is_active=True,
        )
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email=f"owner-{unique_suffix}@example.com",
            username=f"owner-{unique_suffix}",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name=f"Delete Project {unique_suffix}",
            owner_id=user.id,
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        # Soft delete
        project.is_deleted = True
        project.deleted_at = datetime.now(UTC)
        await test_session.commit()

        assert project.is_deleted is True
        assert project.deleted_at is not None
