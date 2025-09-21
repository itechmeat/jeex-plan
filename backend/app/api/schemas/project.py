"""
Project management API schemas.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, validator


class ProjectBase(BaseModel):
    """Base project schema with common fields"""
    name: str = Field(..., min_length=2, max_length=100, description="Project name")
    language: Optional[str] = Field(
        default="en",
        description="Project language code (ISO 639-1)"
    )

    @validator('language')
    def validate_language(cls, v):
        """Validate language code format"""
        if v and len(v) != 2:
            raise ValueError('Language code must be 2 characters (ISO 639-1)')
        return v.lower() if v else 'en'


class ProjectCreate(ProjectBase):
    """Project creation schema"""
    class Config:
        schema_extra = {
            "example": {
                "name": "My Awesome Project",
                "language": "en"
            }
        }


class ProjectUpdate(BaseModel):
    """Project update schema"""
    name: Optional[str] = Field(
        None,
        min_length=2,
        max_length=100,
        description="Project name"
    )
    language: Optional[str] = Field(
        None,
        description="Project language code (ISO 639-1)"
    )

    @validator('language')
    def validate_language(cls, v):
        """Validate language code format"""
        if v and len(v) != 2:
            raise ValueError('Language code must be 2 characters (ISO 639-1)')
        return v.lower() if v else None

    class Config:
        schema_extra = {
            "example": {
                "name": "Updated Project Name",
                "language": "en"
            }
        }


class DocumentInfo(BaseModel):
    """Document information schema"""
    id: str = Field(..., description="Document identifier")
    type: str = Field(..., description="Document type")
    version: int = Field(..., ge=1, description="Document version")
    title: str = Field(..., description="Document title")
    created_at: datetime = Field(..., description="Document creation timestamp")
    updated_at: datetime = Field(..., description="Document last update timestamp")


class StepProgress(BaseModel):
    """Step progress information schema"""
    step: int = Field(..., ge=1, le=4, description="Step number")
    status: str = Field(..., description="Step status (pending, processing, completed, failed)")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    document_id: Optional[str] = Field(None, description="Associated document ID")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    class Config:
        schema_extra = {
            "example": {
                "step": 1,
                "status": "completed",
                "progress": 100,
                "document_id": "doc_123"
            }
        }


class ProjectResponse(ProjectBase):
    """Project response schema with full details"""
    id: str = Field(..., description="Project identifier")
    status: str = Field(..., description="Project status")
    current_step: int = Field(..., ge=1, le=4, description="Current step number")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Project last update timestamp")
    documents: List[DocumentInfo] = Field(default=[], description="Project documents")
    steps_completed: List[int] = Field(default=[], description="Completed step numbers")

    class Config:
        schema_extra = {
            "example": {
                "id": "project_123",
                "name": "My Awesome Project",
                "status": "draft",
                "current_step": 1,
                "language": "en",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z",
                "documents": [
                    {
                        "id": "doc_123",
                        "type": "description",
                        "version": 1,
                        "title": "Project Description",
                        "created_at": "2024-01-01T12:00:00Z",
                        "updated_at": "2024-01-01T12:30:00Z"
                    }
                ],
                "steps_completed": [1]
            }
        }


class ProjectListResponse(BaseModel):
    """Project list response schema (minimal info)"""
    id: str = Field(..., description="Project identifier")
    name: str = Field(..., description="Project name")
    status: str = Field(..., description="Project status")
    current_step: int = Field(..., ge=1, le=4, description="Current step number")
    language: str = Field(..., description="Project language code")
    created_at: datetime = Field(..., description="Project creation timestamp")
    updated_at: datetime = Field(..., description="Project last update timestamp")

    class Config:
        schema_extra = {
            "example": {
                "id": "project_123",
                "name": "My Awesome Project",
                "status": "draft",
                "current_step": 1,
                "language": "en",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T12:00:00Z"
            }
        }


class ProjectProgress(BaseModel):
    """Project progress response schema"""
    project_id: str = Field(..., description="Project identifier")
    current_step: int = Field(..., ge=1, le=4, description="Current step number")
    steps: dict = Field(..., description="Step progress information")
    overall_progress: int = Field(..., ge=0, le=100, description="Overall progress percentage")

    class Config:
        schema_extra = {
            "example": {
                "project_id": "project_123",
                "current_step": 2,
                "steps": {
                    "step1": {
                        "status": "completed",
                        "progress": 100,
                        "document_id": "doc_123"
                    },
                    "step2": {
                        "status": "processing",
                        "progress": 75,
                        "document_id": None
                    },
                    "step3": {
                        "status": "pending",
                        "progress": 0,
                        "document_id": None
                    },
                    "step4": {
                        "status": "pending",
                        "progress": 0,
                        "document_id": None
                    }
                },
                "overall_progress": 44
            }
        }


class ExportResponse(BaseModel):
    """Export response schema"""
    export_id: str = Field(..., description="Export identifier")
    project_id: str = Field(..., description="Project identifier")
    status: str = Field(..., description="Export status")
    download_url: Optional[str] = Field(None, description="Download URL when ready")
    expires_at: Optional[datetime] = Field(None, description="Export expiration time")
    created_at: datetime = Field(..., description="Export creation timestamp")

    class Config:
        schema_extra = {
            "example": {
                "export_id": "export_123",
                "project_id": "project_123",
                "status": "completed",
                "download_url": "http://localhost:5210/api/v1/exports/export_123/download",
                "expires_at": "2024-01-02T00:00:00Z",
                "created_at": "2024-01-01T12:00:00Z"
            }
        }


class StepInput(BaseModel):
    """Step input data schema"""
    idea_description: Optional[str] = Field(None, description="Initial idea description")
    user_clarifications: Optional[dict] = Field(None, description="User clarifications")
    target_audience: Optional[str] = Field(None, description="Target audience")
    requirements: Optional[dict] = Field(None, description="Project requirements")
    constraints: Optional[dict] = Field(None, description="Project constraints")

    class Config:
        schema_extra = {
            "example": {
                "idea_description": "A mobile app for tracking fitness goals",
                "user_clarifications": {
                    "platform": "iOS and Android",
                    "timeline": "6 months"
                },
                "target_audience": "Fitness enthusiasts aged 18-45",
                "requirements": {
                    "user_registration": "required",
                    "social_features": "desired"
                }
            }
        }