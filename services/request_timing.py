"""Optional request-stage timing output."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any

from config import get_settings

_RUN_STAMP = time.strftime("%Y%m%d_%H%M%S", time.localtime())
_WRITE_LOCK = threading.Lock()


class RequestTimer:
    def __init__(self, path_name: str, protocol: str, model: str) -> None:
        self.path_name = path_name
        self.protocol = protocol
        self.model = model
        self.started_at = time.time()
        self.marks: dict[str, float] = {}

    def mark_started(self, name: str, value: float | None = None) -> None:
        self.marks[name] = value if value is not None else time.time()

    def mark(self, name: str, value: float | None = None) -> None:
        self.marks[name] = value if value is not None else time.time()

    def record(self, request_id: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.started_at)),
            "request_id": request_id,
            "protocol": self.protocol,
            "model": self.model,
        }
        for name, value in sorted(self.marks.items()):
            payload[name] = round(value - self.started_at, 6)
        last_mark = max(self.marks.values(), default=time.time())
        payload["total"] = round(last_mark - self.started_at, 6)
        return payload


def resolve_time_log_dir() -> Path:
    return get_settings().app_log_dir / "time"


def flush_timer(timer: RequestTimer, request_id: str) -> None:
    settings = get_settings()
    if not settings.time_tracking_enabled:
        return
    directory = resolve_time_log_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{timer.path_name}_{_RUN_STAMP}.log"
    line = json.dumps(timer.record(request_id), ensure_ascii=False)
    with _WRITE_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
