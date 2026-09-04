"""Cross-process determinism and Git-boundary behaviour for ``ofa version``.

The output is a contract that CI and manifests will lean on, so it is
exercised through real interpreters rather than in-process only. The source
tree is copied into temporary locations so a checkout can be made clean,
dirty, or absent without ever touching this repository.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Final

import pytest

import ofa
from ofa.core.versioning import render_version_report

SRC: Final = Path(ofa.__file__).resolve().parent.parent

#: Two pinned, distinct, non-zero seeds. Zero disables randomization rather
#: than selecting a seed, so a pair including it would test less than it looks.
SEED_A: Final = "1"
SEED_B: Final = "12345"


def _run(
    arguments: Sequence[str],
    *,
    seed: str = SEED_A,
    source: Path = SRC,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(source)}
    return subprocess.run(
        [sys.executable, *arguments],
        env=env,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def _version(**kwargs: object) -> subprocess.CompletedProcess[str]:
    return _run(["-m", "ofa.cli", "version"], **kwargs)  # type: ignore[arg-type]


def _hash_probe(seed: str) -> int:
    completed = _run(["-c", "print(hash('abc'))"], seed=seed)
    return int(completed.stdout.strip())


# --------------------------------------------------------------------------
# Determinism across processes
# --------------------------------------------------------------------------


def test_the_command_succeeds_in_a_fresh_interpreter() -> None:
    completed = _version()
    assert completed.returncode == 0
    assert completed.stderr == ""
    json.loads(completed.stdout)


def test_output_is_byte_identical_under_different_hash_seeds() -> None:
    first = _version(seed=SEED_A)
    second = _version(seed=SEED_B)

    # The guard: prove the two interpreters really were seeded differently,
    # so the equality below cannot pass vacuously.
    assert _hash_probe(SEED_A) != _hash_probe(SEED_B)

    assert first.stdout == second.stdout


def test_output_is_byte_identical_under_forced_randomization() -> None:
    first = _run(["-R", "-m", "ofa.cli", "version"], seed="random")
    second = _run(["-R", "-m", "ofa.cli", "version"], seed="random")
    assert first.stdout == second.stdout


def test_output_does_not_depend_on_the_working_directory(tmp_path: Path) -> None:
    """Resolution follows the source, not wherever the shell happens to be."""
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    assert _version(cwd=SRC.parent).stdout == _version(cwd=elsewhere).stdout


def test_subprocess_output_matches_this_process() -> None:
    assert _version().stdout == render_version_report()


def test_repeated_invocations_agree() -> None:
    assert _version().stdout == _version().stdout == _version().stdout


# --------------------------------------------------------------------------
# The Git boundary, through real interpreters
# --------------------------------------------------------------------------


def _git(arguments: list[str], directory: Path) -> None:
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=test",
            "-c",
            "user.email=test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            *arguments,
        ],
        cwd=directory,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )


@pytest.fixture
def committed_source(tmp_path: Path) -> Path:
    """A copy of the package inside a throwaway, fully committed repository."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(["init", "--quiet"], root)
    shutil.copytree(SRC / "ofa", root / "ofa")
    _git(["add", "--all"], root)
    _git(["commit", "--quiet", "-m", "vendored"], root)
    return root


def _report(source: Path) -> dict[str, object]:
    completed = _version(source=source)
    assert completed.returncode == 0, completed.stderr
    parsed: dict[str, object] = json.loads(completed.stdout)
    return parsed


def test_a_clean_checkout_reports_clean_with_its_commit(committed_source: Path) -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=committed_source,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    ).stdout.strip()
    assert _report(committed_source)["code_revision"] == {
        "state": "CLEAN",
        "revision": head,
    }


def test_a_dirty_checkout_reports_dirty_with_the_same_commit(
    committed_source: Path,
) -> None:
    clean = _report(committed_source)["code_revision"]
    (committed_source / "ofa" / "scratch.txt").write_text("x", encoding="utf-8")
    dirty = _report(committed_source)["code_revision"]
    assert isinstance(clean, dict)
    assert isinstance(dirty, dict)
    assert dirty["state"] == "DIRTY"
    assert dirty["revision"] == clean["revision"]


def test_outside_a_checkout_the_revision_is_unknown(tmp_path: Path) -> None:
    """An installed package with no repository still reports, and reports null."""
    loose = tmp_path / "loose"
    loose.mkdir()
    shutil.copytree(SRC / "ofa", loose / "ofa")
    assert _report(loose)["code_revision"] == {"state": "UNKNOWN", "revision": None}


def test_an_unknown_revision_is_not_a_failure(tmp_path: Path) -> None:
    loose = tmp_path / "loose"
    loose.mkdir()
    shutil.copytree(SRC / "ofa", loose / "ofa")
    completed = _version(source=loose)
    assert completed.returncode == 0
    assert completed.stderr == ""


def test_no_fabricated_revision_appears_outside_a_checkout(tmp_path: Path) -> None:
    loose = tmp_path / "loose"
    loose.mkdir()
    shutil.copytree(SRC / "ofa", loose / "ofa")
    output = _version(source=loose).stdout
    assert "0000000" not in output
    assert "unknown" not in output.replace('"UNKNOWN"', "")


# --------------------------------------------------------------------------
# Exit criterion 4, end to end
# --------------------------------------------------------------------------


def test_the_command_prints_the_code_revision_and_every_schema_version(
    committed_source: Path,
) -> None:
    """docs/roadmap.md Phase 0 exit criterion 4, proven through the real command."""
    from ofa.core.versioning import SCHEMA_VERSIONS

    parsed = _report(committed_source)
    revision = parsed["code_revision"]
    assert isinstance(revision, dict)
    assert revision["revision"] is not None
    assert parsed["schema_versions"] == dict(SCHEMA_VERSIONS)
    assert dict(SCHEMA_VERSIONS) != {}


def test_a_missing_command_fails_with_a_usage_error() -> None:
    completed = _run(["-m", "ofa.cli"])
    assert completed.returncode == 2
    assert completed.stdout == ""
    assert "usage: ofa" in completed.stderr
