"""
API routes module
"""

from . import agents, auth, health, projects

# Import document generation routes if available
try:
    from . import document_generation

    __all__ = ["agents", "auth", "document_generation", "health", "projects"]
except ModuleNotFoundError:
    # Module doesn't exist - this is expected if not yet implemented
    __all__ = ["agents", "auth", "health", "projects"]
