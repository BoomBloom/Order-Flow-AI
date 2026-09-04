"""Versioned contracts, and the revision of the code that is running.

Three separate things travel together in a version report and must not be
confused with one another:

* The **package version** — the distribution's own version, released and
  bumped by hand.
* The **code revision** — which commit is actually running, and whether the
  working tree matches it. This is what ``docs/data_specification.md``
  section 8 stores as ``code_revision`` in every dataset manifest, and what
  makes a stored result traceable back to the code that produced it.
* The **schema versions** — the versioned contracts the code implements.

A schema version answers "what shape is this data"; a code revision answers
"which code wrote it". A result is reproducible only when both are known, so
a version report reports both and never substitutes one for the other.

Nothing here reads a clock, opens a network connection, or consults a random
source. The Git lookup runs once per process and is cached, so a report is
identical every time it is produced within a process and — for a given
checkout — across processes.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Final

from ofa.core.errors import InvalidCodeRevisionError, VersioningTypeError
from ofa.core.hashing import CANONICAL_FORMAT_VERSION


#: The versioned contracts this code implements, by name.
#:
#: Only contracts that exist **today** appear here. There are no placeholders
#: for schemas a later phase will introduce: a version reported for something
#: unimplemented would be a claim about code that cannot honour it.
#:
#: ``canonical_hash_format`` keeps its own identity deliberately. It is a
#: format generation — ``ofa-canon-1`` — not a semantic version, and it must
#: never be compared, ordered, or incremented as though it were one. Its
#: meaning is defined by ``docs/architecture.md`` section 16 item 10: bumping
#: it changes every digest at once, on purpose.
#:
#: The mapping is read-only and iterates in sorted key order, so a report
#: built from it is byte-stable regardless of definition order.
def _frozen_registry(versions: dict[str, str]) -> MappingProxyType[str, str]:
    """Freeze a registry of contract versions in sorted key order.

    Sorting here rather than relying on definition order means a report is
    byte-stable however the entries were written down, and stays that way as
    entries are added. A separate function so the ordering is exercisable on
    its own: with a single registered contract, sorting one entry proves
    nothing.
    """
    return MappingProxyType(dict(sorted(versions.items())))


SCHEMA_VERSIONS: Final[MappingProxyType[str, str]] = _frozen_registry(
    {"canonical_hash_format": CANONICAL_FORMAT_VERSION}
)

#: A full Git object name: 40 lowercase hexadecimal characters. Abbreviated
#: revisions are not accepted — ``docs/data_specification.md`` section 8 stores
#: a ``<git sha>``, and an abbreviation that is unique today can collide later.
_FULL_REVISION = re.compile(r"\A[0-9a-f]{40}\Z")

#: Bounded so a hung or prompting Git can never block a version report.
_GIT_TIMEOUT_SECONDS: Final = 10


class RevisionState(Enum):
    """Whether the running code is identified by its revision."""

    #: The working tree matches the commit, so the revision names the code.
    CLEAN = "CLEAN"

    #: The commit is known but the working tree has uncommitted changes, so
    #: the revision does **not** fully name the running code. Recorded rather
    #: than hidden: a result produced from a dirty tree is not reproducible
    #: from its revision alone, and that has to be visible.
    DIRTY = "DIRTY"

    #: No revision could be determined — not a Git checkout, Git unavailable,
    #: or an installed package with no repository. Never fabricated.
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True, slots=True)
class CodeRevision:
    """The revision of the running code, and how far it can be trusted.

    ``state`` and ``revision`` are bound by invariant: ``UNKNOWN`` carries no
    revision, and every other state carries a full 40-character lowercase
    hexadecimal one. An unknown revision is therefore *representable* and can
    never be mistaken for a real one — there is no sentinel hash, no zero
    hash, and no empty string standing in for a commit.
    """

    state: RevisionState
    revision: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.state, RevisionState):
            raise VersioningTypeError(
                f"CodeRevision.state must be a RevisionState, not {type(self.state).__name__}"
            )
        if self.state is RevisionState.UNKNOWN:
            if self.revision is not None:
                raise InvalidCodeRevisionError(
                    f"an unknown code revision must carry no hash, got "
                    f"{self.revision!r}; a fabricated revision would be a false "
                    f"claim about which code produced an artifact"
                )
            return
        if self.revision is None:
            raise InvalidCodeRevisionError(f"a {self.state.name} code revision must carry a hash")
        if not isinstance(self.revision, str):
            raise VersioningTypeError(
                f"CodeRevision.revision must be a str, not {type(self.revision).__name__}"
            )
        if not _FULL_REVISION.fullmatch(self.revision):
            raise InvalidCodeRevisionError(
                f"code revision must be 40 lowercase hexadecimal characters, got {self.revision!r}"
            )

    @property
    def is_known(self) -> bool:
        """Whether a revision was determined at all."""
        return self.state is not RevisionState.UNKNOWN


#: Resolved once per process. The answer cannot change while the interpreter
#: runs without the source moving underneath it, and caching keeps a report
#: identical across repeated calls.
_CACHED_REVISION: CodeRevision | None = None

UNKNOWN_REVISION: Final = CodeRevision(state=RevisionState.UNKNOWN, revision=None)


def _run_git(arguments: list[str], directory: Path) -> str | None:
    """Run a read-only Git command, returning ``None`` if it cannot be used.

    Every failure mode collapses to ``None``: Git absent from the system, the
    directory not being a repository, Git refusing the directory as
    untrusted, or the command timing out. None of them may raise, because a
    version report must work from an installed package with no repository at
    all.
    """
    try:
        completed = subprocess.run(
            ["git", *arguments],
            cwd=directory,
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout


def _source_directory() -> Path:
    """The directory holding this module, used as the Git lookup root."""
    return Path(__file__).resolve().parent


def resolve_code_revision(*, directory: Path | None = None) -> CodeRevision:
    """Determine the revision of the running code.

    Resolution is deliberately conservative. A revision is reported only when
    Git names one for the directory the source actually lives in; anything
    else is ``UNKNOWN``. The working tree is then checked, and any difference
    from the commit — staged, unstaged, or untracked — makes the state
    ``DIRTY``, because all three mean the commit no longer names the code.

    ``directory`` overrides the lookup root and bypasses the cache; it exists
    so tests can exercise real checkouts and non-checkouts without touching
    this repository. Ordinary callers pass nothing.
    """
    if directory is not None:
        return _resolve_uncached(directory)
    global _CACHED_REVISION
    if _CACHED_REVISION is None:
        _CACHED_REVISION = _resolve_uncached(_source_directory())
    return _CACHED_REVISION


def _resolve_uncached(directory: Path) -> CodeRevision:
    if not directory.is_dir():
        return UNKNOWN_REVISION
    head = _run_git(["rev-parse", "HEAD"], directory)
    if head is None:
        return UNKNOWN_REVISION
    revision = head.strip()
    if not _FULL_REVISION.fullmatch(revision):
        return UNKNOWN_REVISION
    status = _run_git(["status", "--porcelain"], directory)
    if status is None:
        return UNKNOWN_REVISION
    state = RevisionState.CLEAN if status.strip() == "" else RevisionState.DIRTY
    return CodeRevision(state=state, revision=revision)


def version_report(*, directory: Path | None = None) -> dict[str, object]:
    """The full version report, as a plain structure.

    Contains only facts about the code: the package version, the code
    revision and its state, and every registered schema version. Nothing that
    varies between machines or between runs of the same code — no timestamp,
    no path, no hostname, no process id — appears, which is what lets the
    rendered form be compared byte for byte.
    """
    from ofa import __version__

    revision = resolve_code_revision(directory=directory)
    return {
        "package": {"name": "ofa", "version": __version__},
        "code_revision": {
            "state": revision.state.value,
            "revision": revision.revision,
        },
        "schema_versions": dict(SCHEMA_VERSIONS),
    }


def render_version_report(*, directory: Path | None = None) -> str:
    """The version report as deterministic JSON, ending in a newline.

    Sorted keys and a fixed indent, so the text is stable for a given
    checkout no matter which machine, locale, or hash seed produced it. JSON
    because every other structured record in this project is JSON, and
    because the output is a tested contract that something other than a human
    will eventually read.

    This is *not* the canonical hashing form. That is a tagged encoding built
    for digests, not for display, and the two must not be confused.
    """
    import json

    return (
        json.dumps(
            version_report(directory=directory),
            indent=2,
            sort_keys=True,
            ensure_ascii=True,
        )
        + "\n"
    )
