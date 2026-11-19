"""Typed settings loaded with an explicit .env-first precedence."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from dotenv import dotenv_values

from . import defaults

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


class ConfigurationError(ValueError):
    """Raised when an environment value cannot be parsed."""


@dataclass(frozen=True, slots=True)
class Settings:
    app_env: str
    app_host: str
    app_port: int
    app_log_level: str
    app_log_dir: Path

    database_url: str
    db_echo: bool
    db_pool_size: int
    db_max_overflow: int
    db_pool_recycle_seconds: int

    upstream_timeout_seconds: float
    upstream_connect_timeout_seconds: float
    upstream_max_connections: int
    upstream_max_keepalive_connections: int
    upstream_max_attempts: int
    upstream_retry_base_delay_seconds: float

    key_candidate_limit: int
    default_group_type: str
    request_id_header: str
    model_disable_enabled: bool
    model_disable_list: tuple[str, ...]
    time_tracking_enabled: bool
    redis_enabled: bool
    redis_host: str
    redis_port: int
    redis_db: int
    redis_password: str | None
    redis_default_ttl_seconds: int
    redis_socket_timeout_seconds: float
    auth_l1_cache_ttl_seconds: int
    auth_cache_ttl_seconds: int


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"Invalid boolean value: {value!r}")


def _as_int(value: Any) -> int:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid integer value: {value!r}") from exc


def _as_float(value: Any) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"Invalid float value: {value!r}") from exc


def _as_str(value: Any) -> str:
    return str(value).strip()


def _as_path(value: Any) -> Path:
    path = Path(str(value).strip())
    return path if path.is_absolute() else PROJECT_ROOT / path


def _as_model_disable_list(value: Any) -> tuple[str, ...]:
    raw = str(value or "").strip()
    if not raw:
        return ()
    if raw.startswith("[") and raw.endswith("]"):
        try:
            parsed = __import__("json").loads(raw)
        except (TypeError, ValueError):
            parsed = None
        if isinstance(parsed, list):
            return tuple(str(item).strip() for item in parsed if str(item).strip())
    return tuple(item.strip() for item in raw.split(",") if item.strip())


def _read(
    env_values: dict[str, str | None],
    key: str,
    default: Any,
    parser: Callable[[Any], Any],
) -> Any:
    raw = env_values[key] if key in env_values else default
    return parser(raw)


def load_settings(env_path: Path | str | None = None) -> Settings:
    """Load settings without mutating process environment variables.

    A key present in .env always wins, including an intentionally empty value.
    If the key is absent or the file does not exist, the value from config/defaults.py
    is used.
    """
    path = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    env_values = dotenv_values(path) if path.exists() else {}

    return Settings(
        app_env=_read(env_values, "AIGATEWAY_APP_ENV", defaults.APP_ENV, _as_str),
        app_host=_read(env_values, "AIGATEWAY_HOST", defaults.APP_HOST, _as_str),
        app_port=_read(env_values, "AIGATEWAY_PORT", defaults.APP_PORT, _as_int),
        app_log_level=_read(
            env_values, "AIGATEWAY_LOG_LEVEL", defaults.APP_LOG_LEVEL, _as_str
        ),
        app_log_dir=_read(
            env_values, "AIGATEWAY_LOG_DIR", defaults.APP_LOG_DIR, _as_path
        ),
        database_url=_read(
            env_values, "AIGATEWAY_DATABASE_URL", defaults.DATABASE_URL, _as_str
        ),
        db_echo=_read(env_values, "AIGATEWAY_DB_ECHO", defaults.DB_ECHO, _as_bool),
        db_pool_size=_read(
            env_values, "AIGATEWAY_DB_POOL_SIZE", defaults.DB_POOL_SIZE, _as_int
        ),
        db_max_overflow=_read(
            env_values,
            "AIGATEWAY_DB_MAX_OVERFLOW",
            defaults.DB_MAX_OVERFLOW,
            _as_int,
        ),
        db_pool_recycle_seconds=_read(
            env_values,
            "AIGATEWAY_DB_POOL_RECYCLE_SECONDS",
            defaults.DB_POOL_RECYCLE_SECONDS,
            _as_int,
        ),
        upstream_timeout_seconds=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_TIMEOUT_SECONDS",
            defaults.UPSTREAM_TIMEOUT_SECONDS,
            _as_float,
        ),
        upstream_connect_timeout_seconds=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_CONNECT_TIMEOUT_SECONDS",
            defaults.UPSTREAM_CONNECT_TIMEOUT_SECONDS,
            _as_float,
        ),
        upstream_max_connections=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_MAX_CONNECTIONS",
            defaults.UPSTREAM_MAX_CONNECTIONS,
            _as_int,
        ),
        upstream_max_keepalive_connections=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_MAX_KEEPALIVE_CONNECTIONS",
            defaults.UPSTREAM_MAX_KEEPALIVE_CONNECTIONS,
            _as_int,
        ),
        upstream_max_attempts=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_MAX_ATTEMPTS",
            defaults.UPSTREAM_MAX_ATTEMPTS,
            _as_int,
        ),
        upstream_retry_base_delay_seconds=_read(
            env_values,
            "AIGATEWAY_UPSTREAM_RETRY_BASE_DELAY_SECONDS",
            defaults.UPSTREAM_RETRY_BASE_DELAY_SECONDS,
            _as_float,
        ),
        key_candidate_limit=_read(
            env_values,
            "AIGATEWAY_KEY_CANDIDATE_LIMIT",
            defaults.KEY_CANDIDATE_LIMIT,
            _as_int,
        ),
        default_group_type=_read(
            env_values,
            "AIGATEWAY_DEFAULT_GROUP_TYPE",
            defaults.DEFAULT_GROUP_TYPE,
            _as_str,
        ).upper(),
        request_id_header=_read(
            env_values,
            "AIGATEWAY_REQUEST_ID_HEADER",
            defaults.REQUEST_ID_HEADER,
            _as_str,
        ),
        model_disable_enabled=_read(
            env_values,
            "AIGATEWAY_MODEL_DISABLE_ENABLED",
            defaults.MODEL_DISABLE_ENABLED,
            _as_bool,
        ),
        model_disable_list=_read(
            env_values,
            "AIGATEWAY_MODEL_DISABLE_LIST",
            defaults.MODEL_DISABLE_LIST,
            _as_model_disable_list,
        ),
        time_tracking_enabled=_read(
            env_values,
            "AIGATEWAY_TIME_TRACKING_ENABLED",
            defaults.TIME_TRACKING_ENABLED,
            _as_bool,
        ),
        redis_enabled=_read(
            env_values,
            "AIGATEWAY_REDIS_ENABLED",
            defaults.REDIS_ENABLED,
            _as_bool,
        ),
        redis_host=_read(
            env_values, "AIGATEWAY_REDIS_HOST", defaults.REDIS_HOST, _as_str
        ),
        redis_port=_read(
            env_values, "AIGATEWAY_REDIS_PORT", defaults.REDIS_PORT, _as_int
        ),
        redis_db=_read(env_values, "AIGATEWAY_REDIS_DB", defaults.REDIS_DB, _as_int),
        redis_password=_read(
            env_values,
            "AIGATEWAY_REDIS_PASSWORD",
            defaults.REDIS_PASSWORD,
            _as_str,
        )
        or None,
        redis_default_ttl_seconds=_read(
            env_values,
            "AIGATEWAY_REDIS_DEFAULT_TTL_SECONDS",
            defaults.REDIS_DEFAULT_TTL_SECONDS,
            _as_int,
        ),
        redis_socket_timeout_seconds=_read(
            env_values,
            "AIGATEWAY_REDIS_SOCKET_TIMEOUT_SECONDS",
            defaults.REDIS_SOCKET_TIMEOUT_SECONDS,
            _as_float,
        ),
        auth_l1_cache_ttl_seconds=_read(
            env_values,
            "AIGATEWAY_AUTH_L1_CACHE_TTL_SECONDS",
            defaults.AUTH_L1_CACHE_TTL_SECONDS,
            _as_int,
        ),
        auth_cache_ttl_seconds=_read(
            env_values,
            "AIGATEWAY_AUTH_CACHE_TTL_SECONDS",
            defaults.AUTH_CACHE_TTL_SECONDS,
            _as_int,
        ),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reload_settings(env_path: Path | str | None = None) -> Settings:
    get_settings.cache_clear()
    if env_path is not None:
        return load_settings(env_path)
    return get_settings()
