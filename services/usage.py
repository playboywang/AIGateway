"""Token usage extraction for supported model API protocols."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_hit_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def merge(self, payload: dict[str, Any]) -> None:
        self.input_tokens = max(
            self.input_tokens,
            _first_int(payload, "input_tokens", "prompt_tokens"),
        )
        self.output_tokens = max(
            self.output_tokens,
            _first_int(payload, "output_tokens", "completion_tokens"),
        )
        self.cache_hit_tokens = max(
            self.cache_hit_tokens,
            _first_int(
                payload,
                "cache_read_input_tokens",
                "prompt_cache_hit_tokens",
                "cached_tokens",
            ),
        )


def _first_int(payload: dict[str, Any], *names: str) -> int:
    for name in names:
        value = payload.get(name)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)
    return 0


def extract_usage(payload: Any) -> TokenUsage:
    usage = TokenUsage()
    _visit(payload, usage)
    return usage


def _visit(value: Any, usage: TokenUsage) -> None:
    if isinstance(value, dict):
        usage_field = value.get("usage")
        if isinstance(usage_field, dict):
            usage.merge(usage_field)
        for child in value.values():
            if isinstance(child, (dict, list)):
                _visit(child, usage)
    elif isinstance(value, list):
        for child in value:
            _visit(child, usage)


class StreamUsageTracker:
    def __init__(self) -> None:
        self.usage = TokenUsage()
        self.first_token_at: datetime | None = None
        self._buffer = ""

    def feed(self, chunk: bytes) -> None:
        self._buffer += chunk.decode("utf-8", errors="ignore")
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self._feed_line(line.strip())

    def finish(self) -> None:
        remaining = self._buffer.strip()
        if remaining:
            self._feed_line(remaining)
        self._buffer = ""

    def _feed_line(self, line: str) -> None:
        if not line or line.startswith(("event:", "id:", "retry:")):
            return
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line or line == "[DONE]":
            return
        try:
            payload = json.loads(line)
        except (TypeError, ValueError):
            return
        if self.first_token_at is None:
            self.first_token_at = datetime.now()
        usage = extract_usage(payload)
        self.usage.input_tokens = max(self.usage.input_tokens, usage.input_tokens)
        self.usage.output_tokens = max(self.usage.output_tokens, usage.output_tokens)
        self.usage.cache_hit_tokens = max(
            self.usage.cache_hit_tokens, usage.cache_hit_tokens
        )
