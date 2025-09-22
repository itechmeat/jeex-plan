"""
Test models for Epic 01 - Multi-tenant foundation.
"""

import pytest
import uuid
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from app.models.tenant import Tenant
from app.models.user import User
from app.models.project import Project, ProjectStatus
from app.models.document import Document, DocumentType, DocumentStatus


class TestTenantModel:
    """Test Tenant model functionality."""

    @pytest.mark.asyncio
    async def test_create_tenant(self, test_session):
        """Test creating a tenant."""
        tenant = Tenant(
            name="Test Company",
            slug="test-company",
            description="A test company",
            is_active=True
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
    async def test_tenant_slug_unique(self, test_session):
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
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)
        return tenant

    @pytest.mark.asyncio
    async def test_create_user(self, test_session, sample_tenant):
        """Test creating a user."""
        user = User(
            tenant_id=sample_tenant.id,
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            is_active=True,
            is_superuser=False
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.id is not None
        assert user.tenant_id == sample_tenant.id
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.is_active is True
        assert user.is_superuser is False
        assert user.is_deleted is False

    @pytest.mark.asyncio
    async def test_user_oauth_fields(self, test_session, sample_tenant):
        """Test user OAuth fields."""
        user = User(
            tenant_id=sample_tenant.id,
            email="oauth@example.com",
            username="oauthuser",
            oauth_provider="google",
            oauth_id="google_123456"
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.oauth_provider == "google"
        assert user.oauth_id == "google_123456"

    @pytest.mark.asyncio
    async def test_user_tenant_email_unique(self, test_session, sample_tenant):
        """Test that email is unique within a tenant."""
        user1 = User(
            tenant_id=sample_tenant.id,
            email="same@example.com",
            username="user1"
        )
        user2 = User(
            tenant_id=sample_tenant.id,
            email="same@example.com",
            username="user2"
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
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="owner@example.com",
            username="owner"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        return tenant, user

    @pytest.mark.asyncio
    async def test_create_project(self, test_session, sample_tenant_and_user):
        """Test creating a project."""
        tenant, user = sample_tenant_and_user

        project = Project(
            tenant_id=tenant.id,
            name="Test Project",
            description="A test project",
            status=ProjectStatus.DRAFT,
            owner_id=user.id
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
    async def test_project_status_enum(self, test_session, sample_tenant_and_user):
        """Test project status enum values."""
        tenant, user = sample_tenant_and_user

        for status in ProjectStatus:
            project = Project(
                tenant_id=tenant.id,
                name=f"Project {status.value}",
                status=status,
                owner_id=user.id
            )
            test_session.add(project)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_project_tenant_name_unique(self, test_session, sample_tenant_and_user):
        """Test that project names are unique within a tenant."""
        tenant, user = sample_tenant_and_user

        project1 = Project(
            tenant_id=tenant.id,
            name="Unique Project",
            owner_id=user.id
        )
        project2 = Project(
            tenant_id=tenant.id,
            name="Unique Project",
            owner_id=user.id
        )

        test_session.add(project1)
        test_session.add(project2)

        with pytest.raises(IntegrityError):
            await test_session.commit()


class TestDocumentModel:
    """Test Document model functionality."""

    @pytest.fixture
    async def sample_project_setup(self, test_session):
        """Create sample tenant, user, and project for testing."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="owner@example.com",
            username="owner"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name="Test Project",
            owner_id=user.id
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        return tenant, user, project

    @pytest.mark.asyncio
    async def test_create_document(self, test_session, sample_project_setup):
        """Test creating a document."""
        tenant, user, project = sample_project_setup

        document = Document(
            tenant_id=tenant.id,
            title="Test Document",
            content="This is test content",
            document_type=DocumentType.ARCHITECTURE,
            status=DocumentStatus.PENDING,
            project_id=project.id,
            generation_step=1,
            generation_progress=0
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
    async def test_document_type_enum(self, test_session, sample_project_setup):
        """Test document type enum values."""
        tenant, user, project = sample_project_setup

        for doc_type in DocumentType:
            document = Document(
                tenant_id=tenant.id,
                title=f"Document {doc_type.value}",
                document_type=doc_type,
                status=DocumentStatus.PENDING,
                project_id=project.id
            )
            test_session.add(document)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_document_status_enum(self, test_session, sample_project_setup):
        """Test document status enum values."""
        tenant, user, project = sample_project_setup

        for status in DocumentStatus:
            document = Document(
                tenant_id=tenant.id,
                title=f"Document {status.value}",
                document_type=DocumentType.PLANNING,
                status=status,
                project_id=project.id
            )
            test_session.add(document)

        await test_session.commit()
        # All should be created successfully

    @pytest.mark.asyncio
    async def test_document_generation_metadata(self, test_session, sample_project_setup):
        """Test document generation metadata fields."""
        tenant, user, project = sample_project_setup

        document = Document(
            tenant_id=tenant.id,
            title="Generation Test",
            document_type=DocumentType.TECHNICAL_SPEC,
            status=DocumentStatus.GENERATING,
            project_id=project.id,
            generation_step=3,
            generation_progress=75,
            error_message="Some error occurred"
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
    async def test_tenant_user_relationship(self, test_session):
        """Test tenant-user relationship."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="test@example.com",
            username="testuser"
        )
        test_session.add(user)
        await test_session.commit()

        # Test relationship access (this requires eager loading in real scenarios)
        assert user.tenant_id == tenant.id

    @pytest.mark.asyncio
    async def test_user_project_relationship(self, test_session):
        """Test user-project relationship."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="owner@example.com",
            username="owner"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name="Test Project",
            owner_id=user.id
        )
        test_session.add(project)
        await test_session.commit()

        assert project.owner_id == user.id

    @pytest.mark.asyncio
    async def test_project_document_relationship(self, test_session):
        """Test project-document relationship."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="owner@example.com",
            username="owner"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name="Test Project",
            owner_id=user.id
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        document = Document(
            tenant_id=tenant.id,
            title="Test Document",
            document_type=DocumentType.ARCHITECTURE,
            status=DocumentStatus.PENDING,
            project_id=project.id
        )
        test_session.add(document)
        await test_session.commit()

        assert document.project_id == project.id


class TestSoftDelete:
    """Test soft delete functionality."""

    @pytest.mark.asyncio
    async def test_user_soft_delete(self, test_session):
        """Test user soft delete functionality."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="delete@example.com",
            username="deleteuser"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Soft delete
        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        await test_session.commit()

        assert user.is_deleted is True
        assert user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_project_soft_delete(self, test_session):
        """Test project soft delete functionality."""
        tenant = Tenant(name="Test Tenant", slug="test-tenant")
        test_session.add(tenant)
        await test_session.commit()
        await test_session.refresh(tenant)

        user = User(
            tenant_id=tenant.id,
            email="owner@example.com",
            username="owner"
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        project = Project(
            tenant_id=tenant.id,
            name="Delete Project",
            owner_id=user.id
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)

        # Soft delete
        project.is_deleted = True
        project.deleted_at = datetime.utcnow()
        await test_session.commit()

        assert project.is_deleted is True
        assert project.deleted_at is not None