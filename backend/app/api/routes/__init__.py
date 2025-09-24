"""
API routes module
"""

from . import health, auth, projects, agents

# Import document generation routes if available
try:
    from . import document_generation
    __all__ = ["health", "auth", "projects", "agents", "document_generation"]
except ImportError:
    __all__ = ["health", "auth", "projects", "agents"]