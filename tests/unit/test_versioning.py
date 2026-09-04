"""Example-based tests for schema versions and code-revision resolution."""

from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path
from types import MappingProxyType
from typing import Final

import pytest

import ofa
from ofa.core import versioning
from ofa.core.errors import InvalidCodeRevisionError, OfaError, VersioningTypeError
from ofa.core.hashing import CANONICAL_FORMAT_VERSION
from ofa.core.versioning import (
    SCHEMA_VERSIONS,
    CodeRevision,
    RevisionState,
    render_version_report,
    resolve_code_revision,
    version_report,
)

FULL_HASH: Final = "0123456789abcdef0123456789abcdef01234567"
OTHER_HASH: Final = "fedcba9876543210fedcba9876543210fedcba98"


# --------------------------------------------------------------------------
# Schema-version registry
# --------------------------------------------------------------------------


def test_registry_contains_only_contracts_that_exist_today() -> None:
    assert dict(SCHEMA_VERSIONS) == {"canonical_hash_format": CANONICAL_FORMAT_VERSION}


def test_canonical_hash_format_keeps_its_own_identity() -> None:
    """A format generation, not a semantic version: never ordered or bumped."""
    assert SCHEMA_VERSIONS["canonical_hash_format"] == "ofa-canon-1"
    assert not re.fullmatch(r"\d+\.\d+\.\d+", SCHEMA_VERSIONS["canonical_hash_format"])


def test_registry_is_read_only() -> None:
    assert isinstance(SCHEMA_VERSIONS, MappingProxyType)
    with pytest.raises(TypeError):
        SCHEMA_VERSIONS["injected"] = "1.0.0"  # type: ignore[index]


def test_registry_iterates_in_sorted_order() -> None:
    assert list(SCHEMA_VERSIONS) == sorted(SCHEMA_VERSIONS)


def test_registry_construction_sorts_regardless_of_definition_order() -> None:
    """Exercised directly: sorting a one-entry registry would prove nothing."""
    frozen = versioning._frozen_registry({"zebra": "1", "alpha": "2", "mid": "3"})
    assert list(frozen) == ["alpha", "mid", "zebra"]
    assert isinstance(frozen, MappingProxyType)
    with pytest.raises(TypeError):
        frozen["new"] = "4"  # type: ignore[index]


def test_registry_holds_no_placeholders() -> None:
    for name, version in SCHEMA_VERSIONS.items():
        assert name and isinstance(name, str)
        assert version and isinstance(version, str)
        assert "TODO" not in version
        assert version.strip() == version


def test_registry_names_nothing_unimplemented() -> None:
    """A version for code that does not exist would be a claim it cannot honour."""
    for absent in ("manifest", "canonical_event", "feature", "lookback", "strategy"):
        assert not any(absent in name for name in SCHEMA_VERSIONS)


# --------------------------------------------------------------------------
# CodeRevision invariants
# --------------------------------------------------------------------------


@pytest.mark.parametrize("state", [RevisionState.CLEAN, RevisionState.DIRTY])
def test_a_known_revision_carries_a_full_hash(state: RevisionState) -> None:
    revision = CodeRevision(state=state, revision=FULL_HASH)
    assert revision.revision == FULL_HASH
    assert revision.is_known


def test_an_unknown_revision_carries_no_hash() -> None:
    revision = CodeRevision(state=RevisionState.UNKNOWN, revision=None)
    assert revision.revision is None
    assert not revision.is_known


def test_an_unknown_revision_may_not_carry_a_hash() -> None:
    """There is no sentinel commit standing in for "we do not know"."""
    with pytest.raises(InvalidCodeRevisionError, match="false claim"):
        CodeRevision(state=RevisionState.UNKNOWN, revision=FULL_HASH)


@pytest.mark.parametrize("state", [RevisionState.CLEAN, RevisionState.DIRTY])
def test_a_known_revision_may_not_omit_its_hash(state: RevisionState) -> None:
    with pytest.raises(InvalidCodeRevisionError, match="must carry a hash"):
        CodeRevision(state=state, revision=None)


@pytest.mark.parametrize(
    "value",
    [
        "0123456",
        FULL_HASH.upper(),
        FULL_HASH + "0",
        FULL_HASH[:-1],
        "g" * 40,
        " " + FULL_HASH[1:],
        FULL_HASH[:-1] + "\n",
        "",
    ],
)
def test_a_malformed_hash_is_rejected(value: str) -> None:
    with pytest.raises(InvalidCodeRevisionError, match="40 lowercase hexadecimal"):
        CodeRevision(state=RevisionState.CLEAN, revision=value)


@pytest.mark.parametrize("value", [1, 1.0, True, b"a" * 40, None, object()])
def test_a_non_state_is_rejected(value: object) -> None:
    with pytest.raises(VersioningTypeError, match="RevisionState"):
        CodeRevision(state=value, revision=FULL_HASH)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [1, 1.0, b"a" * 40, ["x"]])
def test_a_non_string_revision_is_rejected(value: object) -> None:
    with pytest.raises((VersioningTypeError, InvalidCodeRevisionError)):
        CodeRevision(state=RevisionState.CLEAN, revision=value)  # type: ignore[arg-type]


def test_revisions_compare_by_value_and_are_immutable() -> None:
    left = CodeRevision(state=RevisionState.CLEAN, revision=FULL_HASH)
    assert left == CodeRevision(state=RevisionState.CLEAN, revision=FULL_HASH)
    assert left != CodeRevision(state=RevisionState.DIRTY, revision=FULL_HASH)
    assert left != CodeRevision(state=RevisionState.CLEAN, revision=OTHER_HASH)
    assert not hasattr(left, "__dict__")
    with pytest.raises((AttributeError, TypeError)):
        left.revision = OTHER_HASH  # type: ignore[misc]


def test_the_three_states_are_exactly_these() -> None:
    assert [state.name for state in RevisionState] == ["CLEAN", "DIRTY", "UNKNOWN"]
    assert all(state.value == state.name for state in RevisionState)


# --------------------------------------------------------------------------
# Resolution against real, temporary checkouts
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
def checkout(tmp_path: Path) -> Path:
    """A throwaway repository with one commit. Never this repository."""
    directory = tmp_path / "checkout"
    directory.mkdir()
    _git(["init", "--quiet"], directory)
    (directory / "tracked.txt").write_text("one\n", encoding="utf-8")
    _git(["add", "tracked.txt"], directory)
    _git(["commit", "--quiet", "-m", "initial"], directory)
    return directory


def _head(directory: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=directory,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return completed.stdout.strip()


def test_a_clean_checkout_resolves_to_its_commit(checkout: Path) -> None:
    revision = resolve_code_revision(directory=checkout)
    assert revision.state is RevisionState.CLEAN
    assert revision.revision == _head(checkout)


def test_an_unstaged_change_makes_the_tree_dirty(checkout: Path) -> None:
    (checkout / "tracked.txt").write_text("two\n", encoding="utf-8")
    revision = resolve_code_revision(directory=checkout)
    assert revision.state is RevisionState.DIRTY
    assert revision.revision == _head(checkout)


def test_a_staged_change_makes_the_tree_dirty(checkout: Path) -> None:
    (checkout / "tracked.txt").write_text("three\n", encoding="utf-8")
    _git(["add", "tracked.txt"], checkout)
    assert resolve_code_revision(directory=checkout).state is RevisionState.DIRTY


def test_an_untracked_file_makes_the_tree_dirty(checkout: Path) -> None:
    """Untracked counts too: the commit no longer names what is running."""
    (checkout / "extra.txt").write_text("new\n", encoding="utf-8")
    assert resolve_code_revision(directory=checkout).state is RevisionState.DIRTY


def test_the_commit_is_unchanged_by_dirtiness(checkout: Path) -> None:
    before = resolve_code_revision(directory=checkout).revision
    (checkout / "tracked.txt").write_text("four\n", encoding="utf-8")
    after = resolve_code_revision(directory=checkout)
    assert after.revision == before
    assert after.state is RevisionState.DIRTY


def test_a_directory_that_is_not_a_checkout_is_unknown(tmp_path: Path) -> None:
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "file.txt").write_text("x", encoding="utf-8")
    revision = resolve_code_revision(directory=plain)
    assert revision.state is RevisionState.UNKNOWN
    assert revision.revision is None


def test_a_missing_directory_is_unknown(tmp_path: Path) -> None:
    assert resolve_code_revision(directory=tmp_path / "absent").state is (RevisionState.UNKNOWN)


def test_resolution_is_repeatable(checkout: Path) -> None:
    assert resolve_code_revision(directory=checkout) == resolve_code_revision(directory=checkout)


def test_the_default_resolution_is_cached_per_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Counted rather than compared by identity.

    An identity check passes vacuously whenever the revision is UNKNOWN,
    because that path returns a module-level singleton: the same object comes
    back whether or not anything was cached.
    """
    calls = 0
    real = versioning._resolve_uncached

    def counting(directory: Path) -> CodeRevision:
        nonlocal calls
        calls += 1
        return real(directory)

    monkeypatch.setattr(versioning, "_resolve_uncached", counting)
    monkeypatch.setattr(versioning, "_CACHED_REVISION", None)

    first = resolve_code_revision()
    second = resolve_code_revision()
    assert first == second
    assert calls == 1


def test_an_explicit_directory_bypasses_the_cache(
    monkeypatch: pytest.MonkeyPatch, checkout: Path
) -> None:
    calls = 0
    real = versioning._resolve_uncached

    def counting(directory: Path) -> CodeRevision:
        nonlocal calls
        calls += 1
        return real(directory)

    monkeypatch.setattr(versioning, "_resolve_uncached", counting)
    resolve_code_revision(directory=checkout)
    resolve_code_revision(directory=checkout)
    assert calls == 2


def test_resolution_never_raises_for_any_directory(tmp_path: Path) -> None:
    """A version report must work from an installed package with no repository."""
    for candidate in (tmp_path, tmp_path / "nope", Path("/"), Path(__file__).parent):
        assert isinstance(resolve_code_revision(directory=candidate), CodeRevision)


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def test_report_has_exactly_the_contracted_keys(checkout: Path) -> None:
    report = version_report(directory=checkout)
    assert set(report) == {"package", "code_revision", "schema_versions"}
    assert report["package"] == {"name": "ofa", "version": ofa.__version__}
    assert report["code_revision"] == {
        "state": "CLEAN",
        "revision": _head(checkout),
    }
    assert report["schema_versions"] == dict(SCHEMA_VERSIONS)


def test_report_states_an_unknown_revision_as_null(tmp_path: Path) -> None:
    report = version_report(directory=tmp_path)
    assert report["code_revision"] == {"state": "UNKNOWN", "revision": None}


def test_rendered_report_is_sorted_json_ending_in_a_newline(checkout: Path) -> None:
    rendered = render_version_report(directory=checkout)
    assert rendered.endswith("\n")
    assert not rendered.endswith("\n\n")
    parsed = json.loads(rendered)
    assert parsed == version_report(directory=checkout)
    assert list(parsed) == sorted(parsed)
    assert list(parsed["code_revision"]) == sorted(parsed["code_revision"])


def test_rendered_report_is_ascii_only(checkout: Path) -> None:
    render_version_report(directory=checkout).encode("ascii")


def test_rendered_report_is_stable_within_a_process(checkout: Path) -> None:
    assert render_version_report(directory=checkout) == render_version_report(directory=checkout)


def test_report_contains_the_code_revision_and_every_schema_version(
    checkout: Path,
) -> None:
    """Phase 0 exit criterion 4, stated as a test."""
    rendered = render_version_report(directory=checkout)
    assert _head(checkout) in rendered
    for name, version in SCHEMA_VERSIONS.items():
        assert name in rendered
        assert version in rendered


def test_report_carries_nothing_environment_specific(checkout: Path) -> None:
    rendered = render_version_report(directory=checkout)
    for leaked in (str(checkout), str(Path.cwd()), str(Path.home())):
        assert leaked not in rendered
    assert not re.search(r"\d{4}-\d{2}-\d{2}", rendered)
    assert not re.search(r"\d{2}:\d{2}:\d{2}", rendered)


# --------------------------------------------------------------------------
# Package version consistency
# --------------------------------------------------------------------------


def test_there_is_one_version_source() -> None:
    """hatchling reads src/ofa/__init__.py; nothing else may declare a version."""
    text = Path("pyproject.toml").read_text(encoding="utf-8")
    assert 'dynamic = ["version"]' in text
    assert 'path = "src/ofa/__init__.py"' in text
    assert not re.search(r"^version\s*=", text, re.MULTILINE)


def test_package_metadata_agrees_with_the_module_when_installed() -> None:
    from importlib.metadata import PackageNotFoundError, version

    try:
        installed = version("ofa")
    except PackageNotFoundError:
        pytest.skip("ofa is not installed in this environment")
    assert installed == ofa.__version__


def test_version_is_a_plain_string() -> None:
    assert isinstance(ofa.__version__, str)
    assert ofa.__version__.strip() == ofa.__version__


# --------------------------------------------------------------------------
# Determinism guarantees, asserted over the parsed module
# --------------------------------------------------------------------------


def _module_tree() -> ast.Module:
    with open(versioning.__file__, encoding="utf-8") as handle:
        return ast.parse(handle.read())


def test_module_imports_no_clock_or_entropy_source() -> None:
    imported: set[str] = set()
    for node in ast.walk(_module_tree()):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported.isdisjoint(
        {"time", "datetime", "random", "secrets", "uuid", "socket", "urllib", "http"}
    )


def test_module_calls_no_nondeterministic_builtin() -> None:
    called = {
        node.func.id
        for node in ast.walk(_module_tree())
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert called.isdisjoint({"id", "hash", "eval", "exec", "input"})


def test_versioning_errors_belong_to_both_families() -> None:
    assert issubclass(VersioningTypeError, OfaError)
    assert issubclass(VersioningTypeError, TypeError)
    assert issubclass(InvalidCodeRevisionError, OfaError)
    assert issubclass(InvalidCodeRevisionError, ValueError)
