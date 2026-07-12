"""Entry point orchestration: wire config, client and logic together."""

from __future__ import annotations

import logging
import os

import httpx

from .config import Config
from .errors import ConfigError, StarGiverError
from .followers import find_users_to_follow_back, follow_back
from .github_client import GitHubClient
from .stars import star_profile_repos
from .state import load_state, save_state

logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """Set up plain, timestamped logging suitable for GitHub Actions output."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )


def _write_github_output(**values: object) -> None:
    """Expose step outputs to GitHub Actions via the ``GITHUB_OUTPUT`` file."""
    output_path = os.environ.get("GITHUB_OUTPUT")
    if not output_path:
        return
    with open(output_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def run(config: Config) -> None:
    """Perform one follow-back + star pass for ``config.target_username``."""
    logger.info("Star Giver starting for @%s", config.target_username)

    with GitHubClient(config) as client:
        current_followers = client.list_followers(config.target_username)
        current_following = client.list_following(config.target_username)
        logger.info(
            "Fetched %d follower(s) and %d following",
            len(current_followers),
            len(current_following),
        )

        previous = load_state(config.state_path)
        new_followers = current_followers - previous.followers
        lost_followers = previous.followers - current_followers
        if new_followers:
            logger.info("New followers (+%d): %s", len(new_followers), ", ".join(sorted(new_followers)))
        if lost_followers:
            logger.info("Lost followers (-%d): %s", len(lost_followers), ", ".join(sorted(lost_followers)))

        # Nothing changed since last run (and we have a real baseline): skip work.
        if current_followers == previous.followers and previous.followers:
            logger.info("No follower changes since last run; nothing to do")
            save_state(config.state_path, current_followers, current_following)
            return

        to_follow = find_users_to_follow_back(current_followers, current_following)
        followed = follow_back(client, to_follow, config.follow_delay_seconds)

        # First run (no baseline): star every follower. Otherwise only new ones.
        star_targets = new_followers if previous.followers else current_followers
        starred = star_profile_repos(client, star_targets, config.star_delay_seconds)

        updated_following = current_following | to_follow
        save_state(config.state_path, current_followers, updated_following)

    logger.info(
        "Done. Newly followed: %d, newly starred: %d, new followers: %d",
        len(followed),
        len(starred),
        len(new_followers),
    )
    _write_github_output(
        follow_count=len(followed),
        star_count=len(starred),
        new_followers=len(new_followers),
    )


def main() -> int:
    """CLI entry point. Returns a process exit code (0 = success)."""
    _configure_logging()
    try:
        config = Config.from_env()
    except ConfigError as exc:
        logger.error("Configuration error: %s", exc)
        return 1

    try:
        run(config)
    except StarGiverError as exc:
        logger.error("%s", exc)
        return 1
    except httpx.HTTPError as exc:
        logger.error("GitHub API request failed: %s", exc)
        return 1
    return 0
