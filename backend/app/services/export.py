"""
Export service for generating ZIP archives of project documentation.
Handles the structured export format according to specs.
"""

import os
import zipfile
import tempfile
import shutil
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime, timezone
from pathlib import Path

from app.models.document_version import DocumentVersion, DocumentType
from app.models.export import Export, ExportStatus
from app.repositories.document_version import DocumentVersionRepository
from app.repositories.export import ExportRepository
from app.repositories.project import ProjectRepository
from app.core.config import settings
from app.core.logger import get_logger
from app.core.database import AsyncSession

logger = get_logger()


class ExportService:
    """Service for generating and managing project exports."""

    def __init__(self, session: AsyncSession, tenant_id: UUID):
        self.session = session
        self.tenant_id = tenant_id
        self.doc_repo = DocumentVersionRepository(session, tenant_id)
        self.export_repo = ExportRepository(session, tenant_id)
        self.project_repo = ProjectRepository(session, tenant_id)

    async def create_export(
        self,
        project_id: UUID,
        user_id: UUID,
        export_format: str = "zip",
        expires_in_hours: int = 24
    ) -> Export:
        """Create a new export request."""
        # Get project info
        project = await self.project_repo.get_by_id(project_id)
        if not project:
            raise ValueError("Project not found")

        # Get all document versions
        documents = await self.doc_repo.get_project_documents(project_id)

        # Create manifest
        manifest = await self._create_manifest(project, documents)

        # Create export record
        export = await self.export_repo.create_export(
            project_id=project_id,
            requested_by=user_id,
            manifest=manifest,
            expires_in_hours=expires_in_hours
        )

        await self.session.commit()
        return export

    async def generate_export(self, export_id: UUID) -> str:
        """Generate the export file."""
        export = await self.export_repo.get_by_id(export_id)
        if not export:
            raise ValueError("Export not found")

        if export.status != ExportStatus.PENDING.value:
            raise ValueError(f"Export is not in pending status: {export.status}")

        # Mark as generating
        await self.export_repo.start_generation(export_id)
        await self.session.commit()

        try:
            # Generate ZIP file
            file_path = await self._generate_zip_archive(export)

            # Mark as completed
            await self.export_repo.complete_export(export_id, file_path)
            await self.session.commit()

            return file_path

        except Exception as e:
            # Mark as failed
            await self.export_repo.fail_export(export_id, str(e))
            await self.session.commit()
            raise

    async def _create_manifest(
        self,
        project: Any,
        documents: List[DocumentVersion]
    ) -> Dict[str, Any]:
        """Create export manifest."""
        # Group documents by type
        doc_by_type = {}
        epic_docs = []

        for doc in documents:
            if doc.document_type == DocumentType.PLAN_EPIC.value:
                epic_docs.append({
                    "id": str(doc.id),
                    "epic_number": doc.epic_number,
                    "epic_name": doc.epic_name,
                    "title": doc.title,
                    "version": doc.version,
                    "created_at": doc.created_at.isoformat()
                })
            else:
                doc_by_type[doc.document_type] = {
                    "id": str(doc.id),
                    "title": doc.title,
                    "version": doc.version,
                    "created_at": doc.created_at.isoformat()
                }

        return {
            "project": {
                "id": str(project.id),
                "name": project.name,
                "status": project.status.value,
                "current_step": project.current_step,
                "language": getattr(project, 'language', 'en'),
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat()
            },
            "documents": doc_by_type,
            "epics": epic_docs,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "format": "markdown",
            "version": "1.0"
        }

    async def _generate_zip_archive(self, export: Export) -> str:
        """Generate ZIP archive with structured format."""
        project_id = export.project_id
        manifest = export.manifest

        # Create temporary directory for file structure
        with tempfile.TemporaryDirectory() as temp_dir:
            project_name = manifest["project"]["name"].replace(" ", "-").lower()
            project_dir = Path(temp_dir) / project_name

            # Create directory structure
            project_dir.mkdir()
            docs_dir = project_dir / "docs"
            docs_dir.mkdir()
            plans_dir = docs_dir / "plans"
            plans_dir.mkdir()

            # Generate README.md
            await self._create_readme(project_dir, manifest)

            # Get and save documents
            documents = await self.doc_repo.get_project_documents(project_id)

            for doc in documents:
                if doc.document_type == DocumentType.ABOUT.value:
                    await self._save_document(docs_dir / "about.md", doc)
                elif doc.document_type == DocumentType.ARCHITECTURE.value:
                    await self._save_document(docs_dir / "architecture.md", doc)
                elif doc.document_type == DocumentType.SPECS.value:
                    await self._save_document(docs_dir / "specs.md", doc)
                elif doc.document_type == DocumentType.PLAN_OVERVIEW.value:
                    await self._save_document(plans_dir / "overview.md", doc)
                elif doc.document_type == DocumentType.PLAN_EPIC.value:
                    filename = f"{doc.epic_number:02d}-{doc.epic_name.lower().replace(' ', '-')}.md"
                    await self._save_document(plans_dir / filename, doc)

            # Create ZIP file
            export_dir = Path(settings.EXPORT_DIR)
            export_dir.mkdir(exist_ok=True)

            zip_filename = f"{project_name}-{export.id}.zip"
            zip_path = export_dir / zip_filename

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in project_dir.rglob('*'):
                    if file_path.is_file():
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)

            return str(zip_path)

    async def _create_readme(self, project_dir: Path, manifest: Dict[str, Any]) -> None:
        """Create README.md file."""
        project_info = manifest["project"]

        readme_content = f"""# {project_info["name"]}

## Project Overview

This is an AI-generated documentation package for {project_info["name"]}.

**Project Status:** {project_info["status"].upper()}
**Current Step:** {project_info["current_step"]}/4
**Language:** {project_info["language"]}
**Generated:** {manifest["generated_at"]}

## Documentation Structure

### Core Documents

- **[docs/about.md](docs/about.md)** - Project vision, goals, target audience (PRD style)
- **[docs/architecture.md](docs/architecture.md)** - Technical architecture and design decisions
- **[docs/specs.md](docs/specs.md)** - Development standards, DoD, code guidelines

### Implementation Planning

- **[docs/plans/overview.md](docs/plans/overview.md)** - High-level implementation strategy and roadmap
"""

        # Add epic documentation links
        if manifest.get("epics"):
            readme_content += "\n#### Epic Documentation\n\n"
            for epic in sorted(manifest["epics"], key=lambda x: x["epic_number"]):
                filename = f"{epic['epic_number']:02d}-{epic['epic_name'].lower().replace(' ', '-')}.md"
                readme_content += f"- **[docs/plans/{filename}](docs/plans/{filename})** - {epic['title']}\n"

        readme_content += f"""

## Generation Details

- **Format:** {manifest["format"]}
- **Version:** {manifest["version"]}
- **Total Documents:** {len(manifest["documents"]) + len(manifest.get("epics", []))}
- **Project Created:** {project_info["created_at"]}
- **Last Updated:** {project_info["updated_at"]}

---

*This documentation was generated by JEEX Plan - AI-powered documentation management system.*
"""

        with open(project_dir / "README.md", "w", encoding="utf-8") as f:
            f.write(readme_content)

    async def _save_document(self, file_path: Path, doc: DocumentVersion) -> None:
        """Save a document to file with metadata header."""
        # Create metadata header
        header = f"""---
title: {doc.title}
type: {doc.document_type}
version: {doc.version}
created: {doc.created_at.isoformat()}
"""

        if doc.epic_number is not None:
            header += f"epic_number: {doc.epic_number}\n"
        if doc.epic_name:
            header += f"epic_name: {doc.epic_name}\n"

        if doc.metadata:
            for key, value in doc.metadata.items():
                if key not in ['correlation_id']:  # Skip internal metadata
                    header += f"{key}: {value}\n"

        header += "---\n\n"

        # Write file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(header)
            f.write(doc.content)

    async def get_export_file_path(self, export_id: UUID) -> Optional[str]:
        """Get file path for a completed export."""
        export = await self.export_repo.get_by_id(export_id)
        if not export:
            return None

        if not export.is_downloadable:
            return None

        # Verify file exists
        if export.file_path and os.path.exists(export.file_path):
            return export.file_path

        return None

    async def cleanup_expired_exports(self) -> int:
        """Clean up expired exports."""
        # Get expired exports
        expired_exports = await self.export_repo.get_expired_exports()

        if not expired_exports:
            return 0

        # Delete files and mark as expired
        deleted_count = 0
        export_ids = []

        for export in expired_exports:
            export_ids.append(export.id)

            # Delete file if it exists
            if export.file_path and os.path.exists(export.file_path):
                try:
                    os.remove(export.file_path)
                    deleted_count += 1
                except OSError as e:
                    logger.warning(f"Failed to delete export file {export.file_path}: {e}")

        # Mark as expired
        if export_ids:
            await self.export_repo.mark_expired(export_ids)
            await self.session.commit()

        logger.info(f"Cleaned up {deleted_count} expired export files")
        return deleted_count

    async def get_user_exports(
        self,
        user_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Export]:
        """Get exports for a user."""
        return await self.export_repo.get_user_exports(
            requested_by=user_id,
            limit=limit,
            offset=offset
        )

    async def get_project_exports(
        self,
        project_id: UUID,
        limit: int = 20,
        offset: int = 0
    ) -> List[Export]:
        """Get exports for a project."""
        return await self.export_repo.get_project_exports(
            project_id=project_id,
            limit=limit,
            offset=offset
        )