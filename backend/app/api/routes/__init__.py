"""
API routes module
"""

from . import agents, auth, health, projects

# Import document generation routes if available
try:
    from . import document_generation

    __all__ = ["agents", "auth", "document_generation", "health", "projects"]
except ImportError as e:
    # Only catch ImportError for the specific module, not nested dependency issues
    if isinstance(e, ImportError) and getattr(e, "name", None) in [
        "document_generation",
        __name__ + ".document_generation"
    ]:
        __all__ = ["agents", "auth", "health", "projects"]
    else:
        raise
