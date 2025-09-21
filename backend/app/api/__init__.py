"""
FastAPI application routes and schemas.
"""

from .routes import health, auth, projects
from .schemas import auth as auth_schemas, project as project_schemas

__all__ = [
    "health",
    "auth",
    "projects",
    "auth_schemas",
    "project_schemas",
]