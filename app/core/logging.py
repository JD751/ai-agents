"""Structured JSON logging configuration for the application."""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.config.settings import Settings


class StructuredFormatter(logging.Formatter):
    """Formats log records as single-line JSON."""

    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            data["exception"] = self.formatException(record.exc_info)

        # include any custom attributes passed via extra={}
        skip = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "exc_info",
            "exc_text",
            "thread",
            "threadName",
            "message",
            "taskName",
        }
        for key, value in vars(record).items():
            if key not in skip and not key.startswith("_"):
                data[key] = value

        return json.dumps(data, default=str)


def configure_logging() -> None:
    """Configure root logger with JSON formatter and level from settings."""
    settings = Settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(level)

    # avoid duplicate handlers if configure_logging is called more than once
    for handler in list(root.handlers):
        root.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(StructuredFormatter())
    root.addHandler(handler)

    # reduce noisy third-party logs
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for a given module name."""
    return logging.getLogger(name)
