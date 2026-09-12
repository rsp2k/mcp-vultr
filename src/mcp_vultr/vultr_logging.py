"""
Structured logging configuration for mcp-vultr.

This module sets up structured logging using structlog for better
observability and debugging capabilities.
"""

import logging
import os
import sys
from typing import Any

import structlog

#: Environment variable that sets the log level (DEBUG, INFO, WARNING, ERROR).
LOG_LEVEL_ENV_VAR = "MCP_VULTR_LOG_LEVEL"

#: Default level when the environment does not say otherwise.
DEFAULT_LOG_LEVEL = "WARNING"


def configure_logging(
    level: str | None = None,
    json_logs: bool = False,
    service_name: str = "mcp-vultr",
) -> structlog.BoundLogger:
    """
    Configure structured logging for the application.

    All log output goes to **stderr**. Under the stdio MCP transport stdout is
    the JSON-RPC channel, and anything else written there corrupts the stream.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR). Defaults to
            ``MCP_VULTR_LOG_LEVEL`` from the environment, then ``WARNING``.
        json_logs: Whether to output JSON formatted logs
        service_name: Service name to include in logs

    Returns:
        Configured structlog logger
    """
    if level is None:
        level = os.environ.get(LOG_LEVEL_ENV_VAR, DEFAULT_LOG_LEVEL)
    numeric_level = getattr(logging, level.upper(), logging.WARNING)

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=numeric_level,
    )

    # Configure structlog
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]

    if json_logs:
        processors.extend(
            [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
        )
    else:
        processors.extend([structlog.dev.ConsoleRenderer(colors=True)])

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # Create logger with service context
    logger = structlog.get_logger()
    logger = logger.bind(service=service_name)

    return logger


def _ensure_configured() -> None:
    """
    Apply the stderr configuration unless something already configured structlog.

    structlog's out-of-the-box configuration prints every level to stdout.
    Modules in this package create loggers at import time, so without this
    guard the first debug line lands on stdout before the MCP handshake.
    """
    if not structlog.is_configured():
        configure_logging()


_ensure_configured()


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a logger instance with optional name context.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(logger_name=name)
    return logger


def log_api_request(
    logger: structlog.BoundLogger,
    method: str,
    url: str,
    status_code: int = None,
    response_time: float = None,
    **kwargs: Any,
) -> None:
    """
    Log API request details.

    Args:
        logger: Logger instance
        method: HTTP method
        url: Request URL
        status_code: Response status code
        response_time: Request duration in seconds
        **kwargs: Additional context
    """
    log_data: dict[str, Any] = {"method": method, "url": url, **kwargs}

    if status_code is not None:
        log_data["status_code"] = status_code

    if response_time is not None:
        log_data["response_time"] = response_time

    if status_code and status_code >= 400:
        logger.error("API request failed", **log_data)
    else:
        logger.info("API request completed", **log_data)


def log_mcp_tool_call(
    logger: structlog.BoundLogger,
    tool_name: str,
    success: bool = True,
    duration: float = None,
    **kwargs: Any,
) -> None:
    """
    Log MCP tool execution.

    Args:
        logger: Logger instance
        tool_name: Name of the MCP tool
        success: Whether the tool call was successful
        duration: Execution time in seconds
        **kwargs: Additional context
    """
    log_data: dict[str, Any] = {"tool_name": tool_name, "success": success, **kwargs}

    if duration is not None:
        log_data["duration"] = duration

    if success:
        logger.info("MCP tool executed successfully", **log_data)
    else:
        logger.error("MCP tool execution failed", **log_data)
