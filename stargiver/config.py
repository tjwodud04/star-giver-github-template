"""Runtime configuration for Star Giver.

All tunable values live here as named constants (with optional environment
overrides) so nothing important is hard-coded deep inside the logic.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

# --- Environment variable names -------------------------------------------------
ENV_TOKEN = "GH_PAT"
ENV_TARGET_USERNAME = "TARGET_USERNAME"
# GitHub Actions injects GITHUB_API_URL automatically; falls back to public API.
ENV_API_URL = "GITHUB_API_URL"
ENV_FOLLOW_DELAY = "STARGIVER_FOLLOW_DELAY"
ENV_STAR_DELAY = "STARGIVER_STAR_DELAY"
ENV_REQUEST_TIMEOUT = "STARGIVER_REQUEST_TIMEOUT"
ENV_MAX_RETRIES = "STARGIVER_MAX_RETRIES"

# --- GitHub REST API constants --------------------------------------------------
DEFAULT_API_BASE_URL = "https://api.github.com"
# Pinning the API version is the current GitHub best practice (sent as a header).
GITHUB_API_VERSION = "2022-11-28"
GITHUB_ACCEPT_HEADER = "application/vnd.github+json"
USER_AGENT = "star-giver-github-template"

# --- Behaviour defaults (all overridable via env) -------------------------------
DEFAULT_PER_PAGE = 100
DEFAULT_REQUEST_TIMEOUT_SECONDS = 10.0
DEFAULT_MAX_RETRIES = 3
# Small courtesy pauses between write calls to stay well under abuse limits.
DEFAULT_FOLLOW_DELAY_SECONDS = 0.5
DEFAULT_STAR_DELAY_SECONDS = 0.3
# If a rate-limit reset is further away than this, abort instead of hanging CI.
MAX_RATE_LIMIT_SLEEP_SECONDS = 120.0
# Exponential backoff base for transient (5xx) errors.
BACKOFF_BASE_SECONDS = 1.0
MAX_BACKOFF_SECONDS = 30.0

STATE_FILENAME = "state.json"


def _env_float(name: str, default: float) -> float:
    """Read a float from the environment, falling back to ``default``."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number, got {raw!r}") from exc


def _env_int(name: str, default: int) -> int:
    """Read an int from the environment, falling back to ``default``."""
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


@dataclass(frozen=True)
class Config:
    """Immutable, fully-resolved runtime configuration."""

    token: str
    target_username: str
    api_base_url: str = DEFAULT_API_BASE_URL
    per_page: int = DEFAULT_PER_PAGE
    request_timeout_seconds: float = DEFAULT_REQUEST_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    follow_delay_seconds: float = DEFAULT_FOLLOW_DELAY_SECONDS
    star_delay_seconds: float = DEFAULT_STAR_DELAY_SECONDS
    max_rate_limit_sleep_seconds: float = MAX_RATE_LIMIT_SLEEP_SECONDS
    state_path: Path = Path(STATE_FILENAME)

    @classmethod
    def from_env(cls) -> "Config":
        """Build a :class:`Config` from environment variables.

        Raises:
            ConfigError: if ``GH_PAT`` or ``TARGET_USERNAME`` are missing.
        """
        token = os.environ.get(ENV_TOKEN)
        target_username = os.environ.get(ENV_TARGET_USERNAME)
        missing = [
            name
            for name, value in ((ENV_TOKEN, token), (ENV_TARGET_USERNAME, target_username))
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing required environment variable(s): "
                + ", ".join(missing)
                + ". Set them as a repository secret / variable (see README)."
            )

        # State file sits next to the repository root so GitHub Actions can commit it.
        state_path = Path(__file__).resolve().parent.parent / STATE_FILENAME

        return cls(
            token=token,  # type: ignore[arg-type]  # guaranteed non-None above
            target_username=target_username,  # type: ignore[arg-type]
            api_base_url=os.environ.get(ENV_API_URL, DEFAULT_API_BASE_URL),
            request_timeout_seconds=_env_float(
                ENV_REQUEST_TIMEOUT, DEFAULT_REQUEST_TIMEOUT_SECONDS
            ),
            max_retries=_env_int(ENV_MAX_RETRIES, DEFAULT_MAX_RETRIES),
            follow_delay_seconds=_env_float(ENV_FOLLOW_DELAY, DEFAULT_FOLLOW_DELAY_SECONDS),
            star_delay_seconds=_env_float(ENV_STAR_DELAY, DEFAULT_STAR_DELAY_SECONDS),
            state_path=state_path,
        )
