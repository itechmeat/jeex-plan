"""
Structured logging configuration using structlog.
"""

import logging
import sys

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging for the application"""

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )

    # Set log levels for third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance"""
    return structlog.get_logger(name or "jeex_plan")


class LoggerMixin:
    """Mixin class to add logging capability to other classes"""

    @property
    def logger(self) -> structlog.stdlib.BoundLogger:
        """Get logger for the class"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """Decorator to log function calls with arguments and timing"""
    import functools
    import time

    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.info(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs=list(kwargs.keys()),
        )

        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            logger.info(
                "Function completed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "Function failed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )

            raise

    @functools.wraps(func)
    def sync_wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.info(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs=list(kwargs.keys()),
        )

        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time

            logger.info(
                "Function completed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
            )

            return result

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "Function failed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                error=str(e),
                exc_info=True,
            )

            raise

    if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
        # Async function
        return async_wrapper
    else:
        # Sync function
        return sync_wrapper


# Initialize logging on module import
setup_logging()
