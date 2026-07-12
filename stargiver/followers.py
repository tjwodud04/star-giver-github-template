"""Follow-back logic: mirror the followers you don't yet follow."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from .github_client import GitHubClient

logger = logging.getLogger(__name__)


def find_users_to_follow_back(
    followers: Iterable[str], following: Iterable[str]
) -> set[str]:
    """Return followers that the account does not already follow back."""
    return set(followers) - set(following)


def follow_back(
    client: GitHubClient, usernames: Iterable[str], delay_seconds: float
) -> list[str]:
    """Follow each user in ``usernames``, pausing ``delay_seconds`` between calls.

    Returns:
        The logins that were successfully followed.
    """
    targets = sorted(usernames)
    logger.info("Following back %d user(s)", len(targets))

    followed: list[str] = []
    for username in targets:
        if client.follow_user(username):
            followed.append(username)
        time.sleep(delay_seconds)
    return followed
