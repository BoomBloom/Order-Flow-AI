"""The ``ofa`` command.

``argparse`` and nothing else. ``docs/architecture.md`` section 13 chose "a
thin CLI module" over Typer or Click explicitly, to be revisited only if the
CLI grows; one command is not growth.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ofa.core.versioning import render_version_report

_DESCRIPTION = "Order Flow AI - deterministic quantitative research platform."

_VERSION_HELP = (
    "print the package version, the code revision, and every schema version as deterministic JSON"
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ofa", description=_DESCRIPTION)
    subcommands = parser.add_subparsers(dest="command", metavar="COMMAND")
    subcommands.add_parser("version", help=_VERSION_HELP, description=_VERSION_HELP)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return the process exit status.

    Output goes to stdout with no colour, no locale-dependent formatting, and
    nothing that varies between runs of the same code. A missing or unknown
    command is a usage error, reported on stderr with status 2 — argparse's
    convention, and the one a shell expects.
    """
    parser = _build_parser()
    arguments = parser.parse_args(argv)
    if arguments.command == "version":
        sys.stdout.write(render_version_report())
        return 0
    parser.print_usage(sys.stderr)
    sys.stderr.write("ofa: a command is required (try 'ofa version')\n")
    return 2


if __name__ == "__main__":  # pragma: no cover - exercised through subprocess
    raise SystemExit(main())
