"""
JEEX Plan Backend Application

Multi-agent documentation generation system with FastAPI, PostgreSQL,
Qdrant, Redis, and OpenTelemetry observability.
"""

__version__ = "1.0.0"
__author__ = "JEEX Plan Team"
__email__ = "team@jeex.plan"
__license__ = "MIT"
__status__ = "Development"

from .core import settings
from .main import app

__all__ = ["settings", "app"]