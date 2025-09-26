"""
API routes module
"""

from . import agents, auth, health, projects

# Import document generation routes if available
try:
    from . import document_generation

    __all__ = ["agents", "auth", "document_generation", "health", "projects"]
except ModuleNotFoundError:
    __all__ = ["agents", "auth", "health", "projects"]
except ImportError as e:
    # Allow missing top-level document_generation module but surface other errors
    if isinstance(e, ImportError) and getattr(e, "name", None) in [
        "document_generation",
        __name__ + ".document_generation"
    ]:
        __all__ = ["agents", "auth", "health", "projects"]
    else:
        raise
