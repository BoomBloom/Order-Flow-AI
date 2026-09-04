"""Documented command-line entry points.

``ofa version`` is the only command. ``docs/roadmap.md`` puts every other CLI
command out of scope for Phase 0, and this package stays that small until a
later phase brings a command with real work behind it.
"""

from ofa.cli.main import main

__all__ = ["main"]
