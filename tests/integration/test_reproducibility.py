"""Phase 0 exit criterion 5: two runs produce identical artifacts.

The criterion used to pass because the suite produced nothing to compare.
These tests generate the Phase 0 artifact twice, into two independent
temporary directories, in two separate interpreters under different hash
seeds, and compare the bytes exactly.

Both generations are pinned to the same controlled checkout, so the code
revision — the one part of the artifact that is deliberately
environment-dependent — is the same fact in both, and the comparison is a
comparison of the code's determinism rather than of the machine's.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

from support.phase0_artifact import (
    ARTIFACT_FILENAME,
    ARTIFACT_FORMAT,
    WITNESSES,
    build_artifact,
    render_artifact,
    render_document,
    write_artifact,
)

REPOSITORY: Final = Path(__file__).resolve().parents[2]
SRC: Final = REPOSITORY / "src"
TESTS: Final = REPOSITORY / "tests"

#: Two pinned, distinct, non-zero seeds. Zero disables randomization rather
#: than selecting a seed.
SEED_A: Final = "1"
SEED_B: Final = "12345"

_PROGRAM: Final = """
import sys
from pathlib import Path

from support.phase0_artifact import write_artifact

write_artifact(Path(sys.argv[1]), revision_directory=Path(sys.argv[2]))
print(hash("abc"))
"""


def _generate_in_subprocess(output: Path, seed: str) -> tuple[bytes, int]:
    """Write the artifact from a fresh interpreter; return its bytes and hash seed probe."""
    env = {
        **os.environ,
        "PYTHONHASHSEED": seed,
        "PYTHONPATH": os.pathsep.join([str(SRC), str(TESTS)]),
    }
    completed = subprocess.run(
        [sys.executable, "-c", _PROGRAM, str(output), str(SRC)],
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return (output / ARTIFACT_FILENAME).read_bytes(), int(completed.stdout.strip())


# --------------------------------------------------------------------------
# The criterion
# --------------------------------------------------------------------------


def test_two_independent_generations_are_byte_identical(tmp_path: Path) -> None:
    first = write_artifact(tmp_path / "one", revision_directory=SRC)
    second = write_artifact(tmp_path / "two", revision_directory=SRC)
    assert first != second
    assert first.read_bytes() == second.read_bytes()


def test_two_processes_under_different_hash_seeds_agree(tmp_path: Path) -> None:
    first, first_probe = _generate_in_subprocess(tmp_path / "a", SEED_A)
    second, second_probe = _generate_in_subprocess(tmp_path / "b", SEED_B)

    # The guard: prove the interpreters really were seeded differently, so the
    # equality below cannot pass vacuously.
    assert first_probe != second_probe

    assert first == second


def test_forced_randomization_does_not_change_the_artifact(tmp_path: Path) -> None:
    first, _ = _generate_in_subprocess(tmp_path / "r1", "random")
    second, _ = _generate_in_subprocess(tmp_path / "r2", "random")
    assert first == second


def test_a_subprocess_artifact_matches_one_built_here(tmp_path: Path) -> None:
    produced, _ = _generate_in_subprocess(tmp_path / "child", SEED_A)
    assert produced == render_artifact(revision_directory=SRC)


# --------------------------------------------------------------------------
# The artifact is worth comparing
# --------------------------------------------------------------------------


def test_rendering_sorts_keys_regardless_of_insertion_order() -> None:
    """Exercised directly: the artifact's own keys are already alphabetical."""
    rendered = render_document({"zebra": 1, "alpha": 2, "mid": 3}).decode("ascii")
    assert rendered.index('"alpha"') < rendered.index('"mid"') < rendered.index('"zebra"')
    assert rendered.endswith("}\n")


def test_the_artifact_is_not_a_constant() -> None:
    """It reflects the code: change a witness and the bytes change."""
    baseline = render_artifact(revision_directory=SRC)
    from ofa.core.hashing import content_hash

    assert content_hash(WITNESSES[0][1]).encode("ascii") in baseline


def test_the_artifact_covers_every_canonical_tag() -> None:
    """A witness per tag, so a change to any of them moves the artifact."""
    artifact = build_artifact(revision_directory=SRC)
    witnesses = artifact["witnesses"]
    assert isinstance(witnesses, dict)
    tags = set()
    for entry in witnesses.values():
        assert isinstance(entry, dict)
        canonical = entry["canonical"]
        assert isinstance(canonical, str)
        tags.add(json.loads(canonical)[0])
    assert tags == {
        "none",
        "bool",
        "int",
        "str",
        "bytes",
        "seq",
        "map",
        "enum",
        "flag",
        "price",
        "ticks",
        "utc_nanos",
        "trade_date",
        "run_id",
        "instrument_id",
        "provenance_id",
        "capability_entry",
        "capability_record",
    }


def test_the_artifact_pins_its_own_format_and_contents() -> None:
    artifact = build_artifact(revision_directory=SRC)
    assert artifact["artifact_format"] == ARTIFACT_FORMAT
    assert artifact["witness_count"] == len(WITNESSES)
    assert set(artifact) == {
        "artifact_format",
        "canonical_format",
        "code_revision",
        "package_version",
        "schema_versions",
        "witness_count",
        "witnesses",
    }


def test_witness_labels_are_unique_and_sorted_in_the_artifact() -> None:
    labels = [label for label, _ in WITNESSES]
    assert len(labels) == len(set(labels))
    artifact = build_artifact(revision_directory=SRC)
    witnesses = artifact["witnesses"]
    assert isinstance(witnesses, dict)
    assert list(witnesses) == sorted(labels)


# --------------------------------------------------------------------------
# Nothing environment-specific may leak in
# --------------------------------------------------------------------------


def test_the_artifact_contains_nothing_environment_specific(tmp_path: Path) -> None:
    written = write_artifact(tmp_path / "check", revision_directory=SRC)
    text = written.read_text(encoding="ascii")
    for leaked in (str(tmp_path), str(REPOSITORY), str(Path.home()), str(Path.cwd())):
        assert leaked not in text
    assert not re.search(r"\d{4}-\d{2}-\d{2}T", text)
    assert not re.search(r"\d{2}:\d{2}:\d{2}", text)
    for forbidden in ("hostname", "username", "/tmp", "branch"):
        assert forbidden not in text.lower()


def test_the_artifact_is_pure_ascii(tmp_path: Path) -> None:
    write_artifact(tmp_path / "ascii", revision_directory=SRC).read_text(encoding="ascii")


def test_the_artifact_ends_in_exactly_one_newline(tmp_path: Path) -> None:
    raw = write_artifact(tmp_path / "nl", revision_directory=SRC).read_bytes()
    assert raw.endswith(b"\n")
    assert not raw.endswith(b"\n\n")


def test_the_artifact_pins_the_controlled_revision(tmp_path: Path) -> None:
    """Both runs describe the same checkout, so the revision is a shared fact."""
    from ofa.core.versioning import resolve_code_revision

    expected = resolve_code_revision(directory=SRC)
    artifact = build_artifact(revision_directory=SRC)
    assert artifact["code_revision"] == {
        "state": expected.state.value,
        "revision": expected.revision,
    }


def test_an_unknown_revision_still_produces_a_reproducible_artifact(
    tmp_path: Path,
) -> None:
    """Outside a checkout the revision is null, and the bytes still agree."""
    outside = tmp_path / "outside"
    outside.mkdir()
    first = render_artifact(revision_directory=outside)
    second = render_artifact(revision_directory=outside)
    assert first == second
    assert json.loads(first)["code_revision"] == {
        "state": "UNKNOWN",
        "revision": None,
    }


# --------------------------------------------------------------------------
# Where it is written
# --------------------------------------------------------------------------


def test_the_artifact_is_written_where_the_caller_asks(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "deeper"
    written = write_artifact(target, revision_directory=SRC)
    assert written == target / ARTIFACT_FILENAME
    assert written.is_file()


def test_the_artifact_never_goes_into_the_repository_data_directory(
    tmp_path: Path,
) -> None:
    write_artifact(tmp_path / "somewhere", revision_directory=SRC)
    assert not (REPOSITORY / "data").exists()


@pytest.mark.parametrize("seed", [SEED_A, SEED_B, "random"])
def test_repeated_subprocess_generations_agree(tmp_path: Path, seed: str) -> None:
    first, _ = _generate_in_subprocess(tmp_path / f"one-{seed}", seed)
    second, _ = _generate_in_subprocess(tmp_path / f"two-{seed}", seed)
    assert first == second
