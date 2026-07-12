"""Star logic: star the profile-README repo (``user/user``) of each follower."""

from __future__ import annotations

import logging
import time
from typing import Iterable

from .github_client import GitHubClient

logger = logging.getLogger(__name__)


def star_profile_repos(
    client: GitHubClient, usernames: Iterable[str], delay_seconds: float
) -> list[str]:
    """Star each user's profile-README repository, skipping absent/already-starred.

    A GitHub "profile README" lives in a special repo whose name equals the
    username (e.g. ``octocat/octocat``). We star that repo when it exists.

    Returns:
        The ``owner/repo`` slugs that were newly starred.
    """
    targets = sorted(usernames)
    logger.info("Starring profile READMEs for %d user(s)", len(targets))

    starred: list[str] = []
    for username in targets:
        # The profile-README repo is always named after the user.
        owner = repo = username

        if not client.repo_exists(owner, repo):
            logger.info("%s/%s does not exist; skipping", owner, repo)
            continue
        if client.is_repo_starred(owner, repo):
            logger.info("%s/%s already starred; skipping", owner, repo)
            continue
        if client.star_repo(owner, repo):
            starred.append(f"{owner}/{repo}")
        time.sleep(delay_seconds)
    return starred
