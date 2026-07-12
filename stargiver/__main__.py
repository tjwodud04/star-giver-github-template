"""Allow running the package with ``python -m stargiver``."""

from __future__ import annotations

from .app import main

if __name__ == "__main__":
    raise SystemExit(main())
