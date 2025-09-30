"""
Core application modules.
"""

from .config import settings
from .database import create_tables, get_db
from .logger import get_logger, log_function_call

if settings.ENABLE_OBSERVABILITY:
    from .observability import get_meter, get_tracer, setup_observability
else:
    from .observability import NOOP_GET_METER as get_meter
    from .observability import NOOP_GET_TRACER as get_tracer
    from .observability import NOOP_SETUP_OBSERVABILITY as setup_observability

__all__ = [
    "create_tables",
    "get_db",
    "get_logger",
    "get_meter",
    "get_tracer",
    "log_function_call",
    "settings",
    "setup_observability",
]
