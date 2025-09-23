"""
Core application modules.
"""

from .config import settings
from .database import get_db, create_tables
from .logger import get_logger, log_function_call

if settings.ENABLE_OBSERVABILITY:
    from .observability import setup_observability, get_tracer, get_meter
else:
    from .observability import (
        NOOP_SETUP_OBSERVABILITY as setup_observability,
        NOOP_GET_TRACER as get_tracer,
        NOOP_GET_METER as get_meter,
    )

__all__ = [
    "settings",
    "get_db",
    "create_tables",
    "get_logger",
    "log_function_call",
    "setup_observability",
    "get_tracer",
    "get_meter",
]
