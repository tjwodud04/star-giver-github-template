"""Custom exception types raised across the Star Giver package."""

from __future__ import annotations


class StarGiverError(Exception):
    """Base class for all errors raised by this project."""


class ConfigError(StarGiverError):
    """Raised when required configuration (env vars) is missing or invalid."""


class GitHubApiError(StarGiverError):
    """Raised when the GitHub REST API returns an unrecoverable error."""


class AuthenticationError(GitHubApiError):
    """Raised when the token is missing, invalid or lacks required permissions."""


class RateLimitError(GitHubApiError):
    """Raised when the GitHub rate limit cannot be waited out in a sane time."""
