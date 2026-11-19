"""Application logging setup with request correlation."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

from config import Settings, get_settings
from middleware.request_context import request_id_context

_initialized = False


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


def _build_handler(path: Path, level: int) -> logging.Handler:
    handler = TimedRotatingFileHandler(
        path,
        when="midnight",
        backupCount=14,
        encoding="utf-8",
    )
    handler.setLevel(level)
    return handler


def setup_logging(settings: Settings | None = None) -> None:
    global _initialized
    if _initialized:
        return

    settings = settings or get_settings()
    level = getattr(logging, settings.app_log_level.upper(), logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(request_id)s] %(name)s:%(lineno)d - %(message)s"
    )
    request_id_filter = RequestIdFilter()

    handlers: list[logging.Handler] = []
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    console.addFilter(request_id_filter)
    handlers.append(console)

    try:
        settings.app_log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = _build_handler(settings.app_log_dir / "aigateway.log", level)
        file_handler.setFormatter(formatter)
        file_handler.addFilter(request_id_filter)
        handlers.append(file_handler)
    except OSError as exc:
        logging.getLogger(__name__).warning(
            "File logging disabled: %s", exc
        )

    logging.basicConfig(level=level, handlers=handlers, force=True)
    for noisy_logger in ("httpx", "httpcore", "redis", "uvicorn.access"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
    _initialized = True


def reset_logging_for_tests() -> None:
    global _initialized
    for handler in list(logging.root.handlers):
        handler.close()
        logging.root.removeHandler(handler)
    _initialized = False
