"""The deterministic Phase 0 artifact.

``docs/roadmap.md`` Phase 0 exit criterion 5 requires that "two runs of the
test suite produce identical artifacts". Until now the suite produced no
artifact at all, so the criterion passed by having nothing to compare — a
criterion that cannot fail is not a criterion. This module produces one thing
that can.

The artifact is a witness that the deterministic core still computes what it
computed before. It records, for a fixed set of values covering every
canonical tag, the exact canonical bytes and the exact content hash the code
produces right now; alongside the schema versions, the package version, and
the code revision. Two generations of it agree only if canonical
serialization, hashing, the registry, and revision resolution all agree.

Everything in it derives from the code and from values pinned in this file.
Nothing derives from the environment: no wall-clock time, no random value, no
absolute path, no user or host name, no branch name, no temporary directory,
and no unordered iteration. That is what makes byte comparison meaningful
rather than decorative.

The artifact is written where the caller asks. It never goes near ``data/``,
which is for market data and is gitignored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from ofa import __version__
from ofa.core.capability import CapabilityEntry, CapabilityRecord, DataRequirement
from ofa.core.hashing import CANONICAL_FORMAT_VERSION, canonical_bytes, content_hash
from ofa.core.ids import InstrumentId, ProvenanceId, RunId
from ofa.core.lifecycle import ResetReason, RollPolicy
from ofa.core.money import Price, Ticks
from ofa.core.provenance import ProvenanceTier
from ofa.core.time import TradeDate, UtcNanos
from ofa.core.versioning import SCHEMA_VERSIONS, resolve_code_revision

#: The artifact's own format version. Pinned, and bumped deliberately if the
#: artifact's shape ever changes — a comparison between two different formats
#: would be meaningless, so the format has to be part of what is compared.
ARTIFACT_FORMAT: Final = "ofa-phase0-artifact-1"

#: The file the generator writes. A fixed name so two runs into two different
#: directories produce two paths that differ only in their parent.
ARTIFACT_FILENAME: Final = "phase0-artifact.json"

_OBSERVED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.OBSERVED)
_INFERRED: Final = CapabilityEntry(present=True, tier=ProvenanceTier.INFERRED)
_ABSENT: Final = CapabilityEntry(present=False, tier=None)

#: One witness per canonical tag, plus a nested structure that exercises them
#: together. Labels are the sort key, so the order in the artifact is fixed by
#: this file rather than by however the list happens to be written.
WITNESSES: Final[list[tuple[str, object]]] = [
    ("bool", True),
    ("bytes", b"\x00\xff\x10"),
    ("capability_entry_absent", _ABSENT),
    ("capability_entry_present", _OBSERVED),
    (
        "capability_record",
        CapabilityRecord(
            (
                (DataRequirement.TRADES, _OBSERVED),
                (DataRequirement.AGGRESSOR, _INFERRED),
                (DataRequirement.MBO, _ABSENT),
            )
        ),
    ),
    ("enum_provenance_tier", ProvenanceTier.RECONSTRUCTED),
    ("enum_reset_reason", ResetReason.SPLIT_SEGMENT_START),
    ("enum_roll_policy", RollPolicy.CARRY_ADJUSTED),
    ("flag_composite", DataRequirement.TRADES | DataRequirement.BBO),
    ("flag_empty", DataRequirement(0)),
    ("flag_single", DataRequirement.MBP_10),
    ("instrument_id", InstrumentId(1234)),
    ("int_negative", -9223372036854775808),
    ("int_zero", 0),
    ("map_nested", {"outer": {"b": [1, 2], "a": {"deep": True}}}),
    ("none", None),
    ("price", Price(1_500_000_000)),
    ("provenance_id", ProvenanceId(3)),
    ("run_id", RunId("run-2024-03-11-001")),
    ("seq_mixed", [1, "a", None, True]),
    ("str_non_ascii", "été 中文"),
    ("ticks", Ticks(-6)),
    ("trade_date", TradeDate(2024, 3, 11)),
    ("utc_nanos", UtcNanos(-1)),
]


def build_artifact(*, revision_directory: Path | None = None) -> dict[str, object]:
    """Build the artifact as a plain structure.

    ``revision_directory`` steers code-revision resolution so a test can pin
    both generations to the same controlled checkout. Ordinary callers pass
    nothing and get the running code's own revision.
    """
    revision = resolve_code_revision(directory=revision_directory)
    witnesses = {
        label: {
            "canonical": canonical_bytes(value).decode("ascii"),
            "digest": content_hash(value),
        }
        for label, value in sorted(WITNESSES, key=lambda pair: pair[0])
    }
    return {
        "artifact_format": ARTIFACT_FORMAT,
        "canonical_format": CANONICAL_FORMAT_VERSION,
        "code_revision": {
            "state": revision.state.value,
            "revision": revision.revision,
        },
        "package_version": __version__,
        "schema_versions": dict(SCHEMA_VERSIONS),
        "witness_count": len(WITNESSES),
        "witnesses": witnesses,
    }


def render_document(document: dict[str, object]) -> bytes:
    """Render any artifact document to deterministic bytes.

    Sorted keys, a fixed indent, ASCII escaping, and a single trailing
    newline, encoded as ASCII. Bytes rather than text so the reproducibility
    comparison is a byte comparison and not a comparison of two decodings.

    Separate from :func:`build_artifact` so the sorting is exercisable on its
    own: the artifact's own keys are already alphabetical, so sorting them
    proves nothing about whether sorting happens.
    """
    text = json.dumps(document, indent=2, sort_keys=True, ensure_ascii=True)
    return (text + "\n").encode("ascii")


def render_artifact(*, revision_directory: Path | None = None) -> bytes:
    """The Phase 0 artifact as deterministic bytes."""
    return render_document(build_artifact(revision_directory=revision_directory))


def write_artifact(directory: Path, *, revision_directory: Path | None = None) -> Path:
    """Write the artifact into ``directory`` and return the path.

    The caller chooses the directory, and it is never inside the repository's
    ``data/`` tree — that is for market data, which Phase 0 does not have.
    """
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ARTIFACT_FILENAME
    path.write_bytes(render_artifact(revision_directory=revision_directory))
    return path
