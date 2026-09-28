"""Centralised runtime configuration, loaded from the repository-root `.env` file.

Every environment-specific value is resolved once here so the rest of the
backend never calls `os.getenv` directly and so a misconfigured deployment
fails immediately at start-up instead of silently using a fallback.
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv

# backend/config.py -> backend/ -> repository root
BACKEND_DIR = Path(__file__).resolve().parent
BASE_DIR = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"
SCHEME_CONFIG_DIR = DATA_DIR / "scheme_configs"
UPLOAD_DIR = BACKEND_DIR / "uploads"
SAMPLE_DOC_DIR = BASE_DIR / "docs" / "sample-documents"

# The `.env` file sits at the repository root so the frontend and the backend
# read the same file. Existing process environment variables win.
load_dotenv(BASE_DIR / ".env", override=False)

MIN_AUTH_SECRET_LENGTH = 32
MIN_ALLOWED_PASSWORD_LENGTH = 6


class ConfigurationError(RuntimeError):
    """Raised when the process environment is missing a required setting."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(
            f"Required setting {name} is missing. Copy .env.example to .env and fill it in."
        )
    return value


def _positive_int(name: str, default: int, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}, got {value}.")
    return value


def _csv(name: str, default: str) -> List[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


def load_settings() -> "Settings":
    return Settings(
        mongodb_uri=_require("MONGODB_URI"),
        mongodb_db=os.getenv("MONGODB_DB", "arohan_st").strip() or "arohan_st",
        auth_secret=_require("AUTH_SECRET"),
        token_ttl_seconds=_positive_int("TOKEN_TTL_SECONDS", 8 * 60 * 60, 300),
        bootstrap_officer_email=os.getenv("BOOTSTRAP_OFFICER_EMAIL", "").strip().lower(),
        bootstrap_officer_password=os.getenv("BOOTSTRAP_OFFICER_PASSWORD", ""),
        bootstrap_officer_name=os.getenv("BOOTSTRAP_OFFICER_NAME", "MoTA Officer").strip() or "MoTA Officer",
        min_password_length=_positive_int("MIN_PASSWORD_LENGTH", 8, MIN_ALLOWED_PASSWORD_LENGTH),
        allowed_origins=_csv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ),
    )


class Settings:
    """Immutable snapshot of the process configuration."""

    def __init__(
        self,
        *,
        mongodb_uri: str,
        mongodb_db: str,
        auth_secret: str,
        token_ttl_seconds: int,
        bootstrap_officer_email: str,
        bootstrap_officer_password: str,
        bootstrap_officer_name: str,
        min_password_length: int,
        allowed_origins: List[str],
    ) -> None:
        if len(auth_secret) < MIN_AUTH_SECRET_LENGTH:
            raise ConfigurationError(
                f"AUTH_SECRET must be at least {MIN_AUTH_SECRET_LENGTH} characters "
                f"(got {len(auth_secret)}). Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if not mongodb_uri.startswith(("mongodb://", "mongodb+srv://")):
            raise ConfigurationError("MONGODB_URI must start with mongodb:// or mongodb+srv://")
        if min_password_length < MIN_ALLOWED_PASSWORD_LENGTH:
            raise ConfigurationError(
                f"MIN_PASSWORD_LENGTH must be at least {MIN_ALLOWED_PASSWORD_LENGTH}."
            )

        self.mongodb_uri = mongodb_uri
        self.mongodb_db = mongodb_db
        self.auth_secret = auth_secret
        self.token_ttl_seconds = token_ttl_seconds
        self.bootstrap_officer_email = bootstrap_officer_email
        self.bootstrap_officer_password = bootstrap_officer_password
        self.bootstrap_officer_name = bootstrap_officer_name
        self.min_password_length = min_password_length
        self.allowed_origins = allowed_origins

    @property
    def has_bootstrap_officer(self) -> bool:
        return bool(self.bootstrap_officer_email and self.bootstrap_officer_password)


_settings: "Settings | None" = None


def get_settings() -> "Settings":
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings_cache() -> None:
    """Drop the cached settings. Used by tests that manipulate the environment."""
    global _settings
    _settings = None
