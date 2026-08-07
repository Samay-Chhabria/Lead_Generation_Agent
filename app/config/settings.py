"""Typed, environment-driven application settings.

Settings are read from environment variables (optionally populated from a
.env file) and exposed as a single immutable Settings object so the rest of
the application never has to deal with raw strings.

Configuration is validated at startup (see Settings.validate) and any
directories referenced by the configuration are created automatically
(see Settings.prepare).
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from app.config.constants import (
    DEFAULT_BROWSER_TYPE,
    DEFAULT_ENV_FILE,
    DEFAULT_FREELLM_BASE_URL,
    DEFAULT_HEADLESS,
    DEFAULT_LLM_ENABLED,
    DEFAULT_LLM_MODEL,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LOG_DIR,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_LEADS,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_SEARCH_PROVIDER,
    DEFAULT_SLOW_MO,
    DEFAULT_TIMEOUT,
    FREELLM_API_KEY_ENV,
    FREELLM_BASE_URL_ENV,
    LLM_MODEL_ENV,
    LLM_PROVIDER_ALIASES,
    PROJECT_ROOT,
    SUPPORTED_BROWSERS,
    SUPPORTED_LLM_PROVIDERS,
    SUPPORTED_PROVIDERS,
    VALID_LOG_LEVELS,
)
from app.utils.helpers import ensure_directory

_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _env_str(name: str, default: str) -> str:
    """Return the string value of an environment variable."""
    return os.getenv(name, default).strip()


def _env_bool(name: str, default: bool) -> bool:
    """Return the boolean value of an environment variable.

    Raises:
        ValueError: When the variable is set but is not a recognized boolean.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ValueError(f"{name} must be a boolean (got '{raw}').")


def _env_str_any(names: tuple[str, ...], default: str) -> str:
    """Return the first set string value among several env var names."""
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return value.strip()
    return default


def _env_bool_any(names: tuple[str, ...], default: bool) -> bool:
    """Return the first set boolean among several env var names."""
    for name in names:
        if os.getenv(name) is not None:
            return _env_bool(name, default)
    return default


def _env_int_any(names: tuple[str, ...], default: int) -> int:
    """Return the first set integer among several env var names."""
    for name in names:
        if os.getenv(name) is not None:
            return _env_int(name, default)
    return default


def _env_int(name: str, default: int) -> int:
    """Return the integer value of an environment variable.

    Raises:
        ValueError: When the variable is set but is not a valid integer.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer (got '{raw}').") from exc


def _env_path(name: str, default: Path) -> Path:
    """Return the path value of an environment variable.

    Relative paths are resolved against the project root.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    path = Path(raw.strip())
    return path if path.is_absolute() else PROJECT_ROOT / path


def _normalize_llm_provider(name: str) -> str:
    """Normalize ``LLM_PROVIDER`` spellings to the canonical provider name."""
    normalized = name.strip().lower()
    return LLM_PROVIDER_ALIASES.get(normalized, normalized)


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable, typed application configuration."""

    headless: bool
    timeout: int
    max_leads: int
    search_provider: str
    output_dir: Path
    log_dir: Path
    log_level: str
    browser_type: str = DEFAULT_BROWSER_TYPE
    slow_mo: int = DEFAULT_SLOW_MO
    llm_provider: str = DEFAULT_LLM_PROVIDER
    llm_model: str = DEFAULT_LLM_MODEL
    enable_llm: bool = DEFAULT_LLM_ENABLED
    llm_api_key: str = ""
    llm_base_url: str = DEFAULT_FREELLM_BASE_URL

    @classmethod
    def from_env(cls, env_file: Path | str | None = None) -> "Settings":
        """Build settings from environment variables and an optional .env file."""
        path = Path(env_file) if env_file else DEFAULT_ENV_FILE
        load_dotenv(dotenv_path=path, override=False)
        return cls(
            headless=_env_bool_any(("PLAYWRIGHT_HEADLESS", "HEADLESS"), DEFAULT_HEADLESS),
            timeout=_env_int_any(("PLAYWRIGHT_TIMEOUT", "TIMEOUT"), DEFAULT_TIMEOUT),
            max_leads=_env_int_any(("LEAD_MAX_RESULTS", "MAX_LEADS"), DEFAULT_MAX_LEADS),
            search_provider=_env_str("SEARCH_PROVIDER", DEFAULT_SEARCH_PROVIDER).lower(),
            output_dir=_env_path("OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
            log_dir=_env_path("LOG_DIR", DEFAULT_LOG_DIR),
            log_level=_env_str("LOG_LEVEL", DEFAULT_LOG_LEVEL).upper(),
            browser_type=_env_str("BROWSER_TYPE", DEFAULT_BROWSER_TYPE).lower(),
            slow_mo=_env_int("BROWSER_SLOW_MO", DEFAULT_SLOW_MO),
            llm_provider=_normalize_llm_provider(_env_str("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)),
            llm_model=_env_str(LLM_MODEL_ENV, "") or DEFAULT_LLM_MODEL,
            enable_llm=_env_bool("ENABLE_LLM", DEFAULT_LLM_ENABLED),
            llm_api_key=_env_str_any(
                (FREELLM_API_KEY_ENV, "LLM_API_KEY", "FREE_LLM_ROUTER_API_KEY"), ""
            ),
            llm_base_url=_env_str_any(
                (FREELLM_BASE_URL_ENV, "LLM_BASE_URL", "FREE_LLM_ROUTER_BASE_URL"),
                DEFAULT_FREELLM_BASE_URL,
            ),
        )

    @property
    def llm_enabled(self) -> bool:
        """Return True when AI Agent Mode is active.

        AI Agent Mode requires both ``ENABLE_LLM=true`` and a non-empty
        ``FREELLM_API_KEY``. When either is missing the application switches to
        Offline Mode (deterministic planning, no network calls).
        """
        return self.enable_llm and bool(self.llm_api_key)

    @property
    def llm_mode(self) -> str:
        """Return the human-readable LLM mode: ``"ai"`` or ``"offline"``."""
        return "ai" if self.llm_enabled else "offline"

    def validate(self) -> None:
        """Validate the configuration values.

        Raises:
            ValueError: When any configuration value is invalid. All problems
                are collected and reported together.
        """
        errors: list[str] = []
        if self.timeout <= 0:
            errors.append(f"TIMEOUT must be a positive integer (got {self.timeout}).")
        if self.slow_mo < 0:
            errors.append(f"BROWSER_SLOW_MO must be a non-negative integer (got {self.slow_mo}).")
        if self.max_leads <= 0:
            errors.append(f"MAX_LEADS must be a positive integer (got {self.max_leads}).")
        if self.search_provider not in SUPPORTED_PROVIDERS:
            supported = ", ".join(SUPPORTED_PROVIDERS)
            errors.append(
                f"SEARCH_PROVIDER must be one of: {supported} (got '{self.search_provider}')."
            )
        if self.browser_type not in SUPPORTED_BROWSERS:
            supported = ", ".join(SUPPORTED_BROWSERS)
            errors.append(f"BROWSER_TYPE must be one of: {supported} (got '{self.browser_type}').")
        if self.llm_provider not in SUPPORTED_LLM_PROVIDERS:
            supported = ", ".join(SUPPORTED_LLM_PROVIDERS)
            errors.append(f"LLM_PROVIDER must be one of: {supported} (got '{self.llm_provider}').")
        if self.llm_model.strip().lower() != DEFAULT_LLM_MODEL:
            errors.append(
                f"LLM_MODEL must be 'auto' so the FreeLLM Router performs automatic "
                f"model selection (got '{self.llm_model}')."
            )
        if not self.llm_base_url.strip():
            errors.append("FREELLM_BASE_URL must not be empty.")
        if self.log_level not in VALID_LOG_LEVELS:
            levels = ", ".join(VALID_LOG_LEVELS)
            errors.append(f"LOG_LEVEL must be one of: {levels} (got '{self.log_level}').")
        if errors:
            details = "\n".join(f"- {error}" for error in errors)
            raise ValueError(f"Invalid configuration:\n{details}")

    def prepare(self) -> None:
        """Validate settings and ensure the configured directories exist."""
        self.validate()
        ensure_directory(self.output_dir)
        ensure_directory(self.log_dir)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide Settings instance, cached after first call."""
    return Settings.from_env()
