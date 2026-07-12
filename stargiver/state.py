"""Persistence of the previous follower/following snapshot (``state.json``).

The snapshot lets each run detect *new* followers and skip work when nothing
changed. GitHub Actions commits this file back to the repo between runs.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

logger = logging.getLogger(__name__)


@dataclass
class State:
    """A snapshot of followers/following logins from the previous run."""

    followers: set[str] = field(default_factory=set)
    following: set[str] = field(default_factory=set)


def load_state(path: Path) -> State:
    """Load the previous snapshot, returning an empty one if none exists."""
    if not path.exists():
        logger.info("No previous state at %s; treating this as the first run", path)
        return State()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read state file %s (%s); starting fresh", path, exc)
        return State()
    return State(
        followers=set(raw.get("followers", [])),
        following=set(raw.get("following", [])),
    )


def save_state(path: Path, followers: Iterable[str], following: Iterable[str]) -> None:
    """Write the snapshot as sorted, human-readable JSON."""
    payload = {
        "followers": sorted(followers),
        "following": sorted(following),
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Saved state to %s", path)
