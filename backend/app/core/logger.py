"""Structured logging configuration using structlog."""

from __future__ import annotations

import inspect
import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any, cast

import structlog

from app.core.config import settings

BoundLogger = structlog.stdlib.BoundLogger


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
            structlog.processors.JSONRenderer(),
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


def get_logger(name: str | None = None) -> BoundLogger:
    """Get a structured logger instance"""
    return cast(BoundLogger, structlog.get_logger(name or "jeex_plan"))


class LoggerMixin:
    """Mixin class to add logging capability to other classes"""

    @property
    def logger(self) -> BoundLogger:
        """Get logger for the class"""
        return get_logger(self.__class__.__name__)


def log_function_call(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to log function calls with arguments and timing."""

    import functools
    import time

    @functools.wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        logger = get_logger(func.__module__)
        start_time = time.time()

        logger.info(
            "Function called",
            function=func.__name__,
            args_count=len(args),
            kwargs=list(kwargs.keys()),
        )

        try:
            result = await cast(Callable[..., Awaitable[Any]], func)(*args, **kwargs)
            duration = time.time() - start_time

            logger.info(
                "Function completed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
            )

            return result

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "Function failed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                exc_info=True,
            )

            raise

    @functools.wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
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

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "Function failed",
                function=func.__name__,
                duration_ms=round(duration * 1000, 2),
                error=str(exc),
                exc_info=True,
            )

            raise

    if inspect.iscoroutinefunction(func):
        return async_wrapper

    return sync_wrapper


# Initialize logging on module import
setup_logging()
