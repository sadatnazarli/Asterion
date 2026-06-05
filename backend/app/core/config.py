"""Asterion central configuration.

Single source of truth for runtime settings, loaded from environment / .env via
pydantic-settings. No secret literals in code. Every variable mirrors
``.env.example``. Imported as ``from app.core.config import settings``.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Self

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/ directory (where pyproject.toml lives)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


def resolve_env_files() -> tuple[Path, ...]:
    """Absolute paths checked in order (later files do not override earlier os.environ)."""
    candidates = (
        BACKEND_ROOT / ".env",
        PROJECT_ROOT / ".env",
    )
    return tuple(p for p in candidates if p.is_file())


def _env_var_present(name: str) -> bool:
    val = os.getenv(name)
    return bool(val and val.strip())


def _env_first(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


def mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 4:
        return "****"
    return f"****{key[-4:]}"


def load_env_files() -> list[Path]:
    """Load .env files into os.environ without overwriting existing vars."""
    loaded: list[Path] = []
    for path in resolve_env_files():
        for key, value in dotenv_values(path).items():
            if value is None or value == "":
                continue
            if key not in os.environ:
                os.environ[key] = value
        loaded.append(path)
    return loaded


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ASTERION_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- App ---
    env: str = "dev"
    log_level: str = "INFO"
    data_dir: str = "./data"

    # --- Database ---
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "asterion"
    db_user: str = "asterion"
    db_password: str = "change_me"
    embed_dim: int = 768

    # --- Redis / Celery ---
    redis_url: str = "redis://localhost:6379/0"

    # --- Local LLM ---
    llm_enabled: bool = True
    llm_backend: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    llm_model: str = "qwen2.5:7b-instruct"
    llm_reasoning_model: str = "qwen2.5:14b-instruct"
    embed_model: str = "nomic-embed-text"
    llm_timeout_s: int = 120
    llm_max_retries: int = 3
    openai_compat_base_url: str = "http://localhost:1234/v1"
    openai_compat_api_key: str = "not-needed"

    allow_external_llm: bool = False
    external_llm_api_key: str | None = None

    # --- Ingestion & Providers ---
    sec_user_agent: str = Field(default="Asterion Research (set-your-email@example.com)")
    sec_max_rps: int = 8
    prices_provider: str = "fallback"

    finnhub_api_key: str | None = None
    fmp_api_key: str | None = None
    fred_api_key: str | None = None
    polygon_api_key: str | None = None
    openfigi_api_key: str | None = None

    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    @model_validator(mode="after")
    def resolve_api_key_aliases(self) -> Self:
        if not self.finnhub_api_key:
            self.finnhub_api_key = _env_first("ASTERION_FINNHUB_API_KEY", "FINNHUB_API_KEY")
        if not self.fmp_api_key:
            self.fmp_api_key = _env_first("ASTERION_FMP_API_KEY", "FMP_API_KEY")
        if not self.fred_api_key:
            self.fred_api_key = _env_first("ASTERION_FRED_API_KEY", "FRED_API_KEY")
        if not self.polygon_api_key:
            self.polygon_api_key = _env_first("ASTERION_POLYGON_API_KEY", "POLYGON_API_KEY")
        if not self.openfigi_api_key:
            self.openfigi_api_key = _env_first("ASTERION_OPENFIGI_API_KEY", "OPENFIGI_API_KEY")
        return self

    @property
    def db_dsn(self) -> str:
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    @property
    def db_dsn_sync(self) -> str:
        return (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def env_diagnostics(self) -> dict[str, object]:
        loaded = load_env_files()
        return {
            "cwd": os.getcwd(),
            "backend_root": str(BACKEND_ROOT),
            "project_root": str(PROJECT_ROOT),
            "loaded_env_files": [str(p) for p in loaded],
            "checked_env_files": [str(p) for p in resolve_env_files()],
            "FINNHUB_API_KEY_present": _env_var_present("FINNHUB_API_KEY"),
            "ASTERION_FINNHUB_API_KEY_present": _env_var_present("ASTERION_FINNHUB_API_KEY"),
            "finnhub_configured": bool(self.finnhub_api_key),
            "finnhub_masked_key": mask_api_key(self.finnhub_api_key),
        }


@lru_cache
def get_settings() -> Settings:
    load_env_files()
    return Settings()


settings = get_settings()
