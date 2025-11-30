"""Production-ready logging setup using structlog."""

import logging
import sys
from typing import Any

import structlog
from structlog.types import Processor


def setup_logging(debug: bool = False, log_level: str = "INFO") -> None:
    """
    Configure structlog for production-ready logging.

    In debug mode: Pretty console output with colors
    In production: JSON output for log aggregators

    Args:
        debug: Enable debug mode with pretty console output
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string log level to int
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Shared processors for all modes
    # Note: Don't use add_logger_name with PrintLoggerFactory
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        # Development: pretty console output
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    else:
        # Production: JSON output
        processors = shared_processors + [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Also configure standard logging for third-party libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=numeric_level,
    )


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """
    Get a structlog logger instance.

    Args:
        name: Logger name (optional)

    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger(name)
    return logger


# Convenience function for binding context
def bind_context(**kwargs: Any) -> None:
    """Bind context variables to the current context."""
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """Clear all bound context variables."""
    structlog.contextvars.clear_contextvars()
