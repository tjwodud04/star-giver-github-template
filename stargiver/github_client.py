"""A small, typed GitHub REST client built on :mod:`httpx`.

It centralises authentication, pagination, retries and (crucially for an
unattended cron job) graceful rate-limit handling, so the higher-level
follow/star logic can stay simple.
"""

from __future__ import annotations

import logging
import time
from types import TracebackType
from typing import Iterator, Optional

import httpx

from .config import (
    BACKOFF_BASE_SECONDS,
    GITHUB_ACCEPT_HEADER,
    GITHUB_API_VERSION,
    MAX_BACKOFF_SECONDS,
    USER_AGENT,
    Config,
)
from .errors import AuthenticationError, RateLimitError

logger = logging.getLogger(__name__)

# HTTP status codes GitHub uses that this client understands explicitly.
_HTTP_NO_CONTENT = 204
_HTTP_UNAUTHORIZED = 401
_HTTP_FORBIDDEN = 403
_HTTP_NOT_FOUND = 404
_HTTP_TOO_MANY_REQUESTS = 429
_HTTP_SERVER_ERROR = 500


class GitHubClient:
    """Thin wrapper around the GitHub REST API for follow/star operations."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.api_base_url,
            timeout=config.request_timeout_seconds,
            headers={
                "Authorization": f"Bearer {config.token}",
                "Accept": GITHUB_ACCEPT_HEADER,
                "X-GitHub-Api-Version": GITHUB_API_VERSION,
                "User-Agent": USER_AGENT,
            },
        )

    # -- Context manager -------------------------------------------------------
    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        self._client.close()

    # -- Public API ------------------------------------------------------------
    def list_followers(self, username: str) -> set[str]:
        """Return the set of logins that follow ``username``."""
        return {user["login"] for user in self._paginate(f"/users/{username}/followers")}

    def list_following(self, username: str) -> set[str]:
        """Return the set of logins that ``username`` follows."""
        return {user["login"] for user in self._paginate(f"/users/{username}/following")}

    def follow_user(self, username: str) -> bool:
        """Follow ``username`` on behalf of the authenticated user.

        Returns:
            True if GitHub confirmed the follow (idempotent: already-following
            also returns 204), False otherwise.
        """
        response = self._request("PUT", f"/user/following/{username}")
        if response.status_code == _HTTP_NO_CONTENT:
            logger.info("Followed %s", username)
            return True
        logger.warning("Could not follow %s (HTTP %s)", username, response.status_code)
        return False

    def repo_exists(self, owner: str, repo: str) -> bool:
        """Return True if the repository ``owner/repo`` exists and is visible."""
        response = self._request("GET", f"/repos/{owner}/{repo}")
        return response.status_code == httpx.codes.OK

    def is_repo_starred(self, owner: str, repo: str) -> bool:
        """Return True if the authenticated user already starred ``owner/repo``."""
        response = self._request("GET", f"/user/starred/{owner}/{repo}")
        return response.status_code == _HTTP_NO_CONTENT

    def star_repo(self, owner: str, repo: str) -> bool:
        """Star ``owner/repo`` for the authenticated user.

        Returns:
            True if GitHub confirmed the star, False otherwise.
        """
        response = self._request("PUT", f"/user/starred/{owner}/{repo}")
        if response.status_code == _HTTP_NO_CONTENT:
            logger.info("Starred %s/%s", owner, repo)
            return True
        logger.warning(
            "Could not star %s/%s (HTTP %s)", owner, repo, response.status_code
        )
        return False

    # -- Internals -------------------------------------------------------------
    def _paginate(self, path: str) -> Iterator[dict]:
        """Yield every item across all pages, following ``Link`` headers."""
        url: Optional[str] = path
        params: Optional[dict[str, int]] = {"per_page": self._config.per_page}
        while url is not None:
            response = self._request("GET", url, params=params)
            response.raise_for_status()
            yield from response.json()
            # The "next" link already carries per_page/page, so drop our params.
            next_link = response.links.get("next")
            url = next_link["url"] if next_link else None
            params = None

    def _request(
        self, method: str, url: str, params: Optional[dict] = None
    ) -> httpx.Response:
        """Send a request, transparently handling retries and rate limits."""
        last_response: Optional[httpx.Response] = None
        for attempt in range(self._config.max_retries + 1):
            response = self._client.request(method, url, params=params)
            last_response = response

            if response.status_code == _HTTP_UNAUTHORIZED:
                raise AuthenticationError(
                    "GitHub rejected the token (HTTP 401). Check that GH_PAT is "
                    "valid, unexpired and has the required permissions."
                )

            if not self._is_retryable(response):
                return response

            if attempt == self._config.max_retries:
                break

            delay = self._retry_delay(response, attempt)
            logger.warning(
                "%s %s -> HTTP %s; retrying in %.1fs (attempt %d/%d)",
                method,
                url,
                response.status_code,
                delay,
                attempt + 1,
                self._config.max_retries,
            )
            time.sleep(delay)

        assert last_response is not None  # loop always runs at least once
        return last_response

    def _is_retryable(self, response: httpx.Response) -> bool:
        """Return True for transient failures worth retrying."""
        if response.status_code >= _HTTP_SERVER_ERROR:
            return True
        return self._is_rate_limited(response)

    @staticmethod
    def _is_rate_limited(response: httpx.Response) -> bool:
        """Detect GitHub rate limits.

        Covers the 429 form, the primary limit (403 + ``x-ratelimit-remaining: 0``)
        and the secondary/abuse limit (403 carrying a ``Retry-After`` header).
        A plain 403 (e.g. missing token permission) is *not* treated as a limit.
        """
        if response.status_code == _HTTP_TOO_MANY_REQUESTS:
            return True
        if response.status_code != _HTTP_FORBIDDEN:
            return False
        return (
            response.headers.get("x-ratelimit-remaining") == "0"
            or "retry-after" in response.headers
        )

    def _retry_delay(self, response: httpx.Response, attempt: int) -> float:
        """Compute how long to wait before retrying a failed request."""
        # Secondary rate limits provide an explicit Retry-After header.
        retry_after = response.headers.get("retry-after")
        if retry_after and retry_after.isdigit():
            return float(retry_after)

        # Primary rate limits tell us exactly when the window resets.
        if self._is_rate_limited(response):
            reset = response.headers.get("x-ratelimit-reset")
            if reset and reset.isdigit():
                wait = float(reset) - time.time()
                if wait > self._config.max_rate_limit_sleep_seconds:
                    raise RateLimitError(
                        "GitHub rate limit exhausted; reset is "
                        f"{wait:.0f}s away (> "
                        f"{self._config.max_rate_limit_sleep_seconds:.0f}s cap). "
                        "Aborting this run; it will retry on the next schedule."
                    )
                return max(wait, 0.0) + 1.0

        # Transient server errors: exponential backoff.
        return min(BACKOFF_BASE_SECONDS * (2**attempt), MAX_BACKOFF_SECONDS)
