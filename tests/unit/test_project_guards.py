"""Repository-level guards for the Phase 0 exit criteria.

These assert properties of the project rather than of any one function:
that the runtime dependency set is empty, that no market-data SDK is present,
that market data cannot enter the repository, and that the exact price and
time paths contain no floating-point arithmetic. Each is a criterion
``docs/roadmap.md`` states, expressed as something that fails rather than
something a human is expected to notice.
"""

from __future__ import annotations

import ast
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Final

import pytest

REPOSITORY: Final = Path(__file__).resolve().parents[2]
PYPROJECT: Final = REPOSITORY / "pyproject.toml"
PACKAGE: Final = REPOSITORY / "src" / "ofa"
CHECK_WORKFLOW: Final = REPOSITORY / ".github" / "workflows" / "check.yml"


def _pyproject() -> dict[str, object]:
    with open(PYPROJECT, "rb") as handle:
        parsed: dict[str, object] = tomllib.load(handle)
    return parsed


def _project_table() -> dict[str, object]:
    table = _pyproject()["project"]
    assert isinstance(table, dict)
    return table


def _git(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


# --------------------------------------------------------------------------
# Exit criterion 6a — zero runtime dependencies
# --------------------------------------------------------------------------


def test_declared_runtime_dependencies_are_empty() -> None:
    assert _project_table()["dependencies"] == []


def test_every_source_import_is_standard_library_or_first_party() -> None:
    """The structural guard, not a denylist.

    A denylist only catches the packages somebody thought of. This enumerates
    what the shipped package actually imports and requires every root to be
    either the standard library or ``ofa`` itself, so *any* third-party import
    fails — including one nobody anticipated.
    """
    allowed = set(sys.stdlib_module_names) | {"ofa"}
    offenders: dict[str, set[str]] = {}
    for source in sorted(PACKAGE.rglob("*.py")):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        roots: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0 and node.module is not None:
                    roots.add(node.module.split(".")[0])
        outside = {root for root in roots if root not in allowed}
        if outside:
            offenders[str(source.relative_to(REPOSITORY))] = outside
    assert offenders == {}


def test_installed_metadata_gates_every_requirement_behind_an_extra() -> None:
    """Development packages must stay development-only in the built distribution."""
    from importlib.metadata import PackageNotFoundError, distribution

    try:
        requirements = distribution("ofa").requires
    except PackageNotFoundError:
        pytest.skip("ofa is not installed in this environment")
    for requirement in requirements or []:
        assert "extra ==" in requirement, requirement


def test_the_package_imports_with_no_third_party_module_available() -> None:
    """Proven by importing it in a subprocess with an empty import path."""
    program = (
        "import sys\n"
        "sys.path = [p for p in sys.path if 'site-packages' not in p]\n"
        f"sys.path.insert(0, {str(PACKAGE.parent)!r})\n"
        "import ofa, ofa.core, ofa.cli.main\n"
        "print('ok')\n"
    )
    completed = subprocess.run(
        [sys.executable, "-S", "-c", program],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == "ok"


# --------------------------------------------------------------------------
# Exit criterion 6b — no market-data SDK
# --------------------------------------------------------------------------

#: A secondary defence only. Its limitation is exactly the limitation of any
#: denylist: it catches the vendors we happened to name. The guard that
#: actually holds is the structural one above — an empty runtime dependency
#: set with every import resolving to the standard library leaves no room for
#: a market-data SDK, named here or not.
KNOWN_MARKET_DATA_PACKAGES: Final[frozenset[str]] = frozenset(
    {
        "databento",
        "polygon",
        "polygon-api-client",
        "alpaca",
        "alpaca-py",
        "alpaca-trade-api",
        "ccxt",
        "ib-insync",
        "ibapi",
        "iqfeed",
        "quandl",
        "nasdaq-data-link",
        "refinitiv-data",
        "yfinance",
        "tardis-client",
        "tardis-dev",
        "kaiko",
        "coinapi",
        "rithmic",
        "dxfeed",
    }
)


def test_no_market_data_sdk_is_a_runtime_dependency() -> None:
    """Structural: the runtime dependency set is empty, so nothing is in it."""
    assert _project_table()["dependencies"] == []


def test_no_market_data_sdk_appears_in_any_dependency_declaration() -> None:
    """Secondary denylist, over both runtime and development declarations."""
    project = _project_table()
    runtime = project["dependencies"]
    assert isinstance(runtime, list)
    declared: list[str] = list(runtime)
    extras = project.get("optional-dependencies", {})
    assert isinstance(extras, dict)
    for group in extras.values():
        declared.extend(group)
    for requirement in declared:
        name = requirement.split(";")[0].split("==")[0].split(">=")[0].split("[")[0].strip().lower()
        assert name not in KNOWN_MARKET_DATA_PACKAGES, requirement


def test_no_market_data_sdk_is_importable_in_this_environment() -> None:
    """The clean Phase 0 environment has none of them installed."""
    from importlib.util import find_spec

    for package in ("databento", "ccxt", "yfinance", "ib_insync", "polygon"):
        assert find_spec(package) is None, package


# --------------------------------------------------------------------------
# Exit criterion 6c — `data/` never enters the repository
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "candidate",
    [
        "data/raw/file.dbn",
        "data/canonical/GLBX/NQ/2024-03-11/trades.parquet",
        "data/runs/r1/manifest.json",
        "data/anything",
    ],
)
def test_git_ignores_everything_under_data(candidate: str) -> None:
    """Asked of git itself, not matched against .gitignore text."""
    assert _git(["check-ignore", "-q", candidate]).returncode == 0, candidate


def test_no_data_artifact_is_tracked() -> None:
    tracked = _git(["ls-files"]).stdout.splitlines()
    offenders = [
        path
        for path in tracked
        if path.startswith("data/") or path.endswith((".parquet", ".dbn", ".dbn.zst"))
    ]
    assert offenders == []


def test_the_repository_has_no_data_directory() -> None:
    """Phase 0 produces no market data, so the directory should not exist."""
    assert not (REPOSITORY / "data").exists()


def test_generating_the_artifact_leaves_the_repository_untouched(
    tmp_path: Path,
) -> None:
    """The suite writes its artifact to a temporary location, never in-tree."""
    from support.phase0_artifact import write_artifact

    before = _git(["status", "--porcelain", "--untracked-files=all"]).stdout
    written = write_artifact(tmp_path / "out")
    assert written.is_file()
    assert not str(written).startswith(str(REPOSITORY))
    after = _git(["status", "--porcelain", "--untracked-files=all"]).stdout
    assert after == before
    assert not (REPOSITORY / "data").exists()


def test_ci_environment_is_created_outside_the_checkout() -> None:
    """CI tooling must not make the source tree dirty before it is verified."""
    workflow = CHECK_WORKFLOW.read_text(encoding="utf-8")
    assert ".ci-venv" not in workflow
    assert "CI_VENV=${RUNNER_TEMP}/ofa-ci-venv" in workflow
    assert '"${CI_VENV}/bin/python"' in workflow
    assert '"${CI_VENV}/bin/ofa"' in workflow
    assert "git status --porcelain --untracked-files=all" in workflow


# --------------------------------------------------------------------------
# Exit criterion 2 — no floating point in the exact paths
# --------------------------------------------------------------------------

EXACT_MODULES: Final[list[str]] = [
    "core/money.py",
    "core/time.py",
    "core/hashing.py",
    "core/ids.py",
    "core/capability.py",
    "core/provenance.py",
    "core/lifecycle.py",
    "core/versioning.py",
]


def _tree(relative: str) -> ast.Module:
    return ast.parse((PACKAGE / relative).read_text(encoding="utf-8"))


@pytest.mark.parametrize("relative", EXACT_MODULES)
def test_no_float_literal_appears_in_an_exact_module(relative: str) -> None:
    literals = [
        node
        for node in ast.walk(_tree(relative))
        if isinstance(node, ast.Constant) and isinstance(node.value, float)
    ]
    assert literals == []


@pytest.mark.parametrize("relative", EXACT_MODULES)
def test_no_true_division_appears_in_an_exact_module(relative: str) -> None:
    """`/` yields a float even between two integers; `//` and divmod do not."""
    divisions = [
        node
        for node in ast.walk(_tree(relative))
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div)
    ]
    assert divisions == []


@pytest.mark.parametrize("relative", EXACT_MODULES)
def test_nothing_is_converted_to_a_float_in_an_exact_module(relative: str) -> None:
    conversions = [
        node
        for node in ast.walk(_tree(relative))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"float", "complex"}
    ]
    assert conversions == []


# --------------------------------------------------------------------------
# Toolchain pinning
# --------------------------------------------------------------------------


def test_every_development_dependency_is_pinned_exactly() -> None:
    """A floating range makes "green on a clean clone" depend on release dates."""
    extras = _project_table()["optional-dependencies"]
    assert isinstance(extras, dict)
    development = extras["dev"]
    assert isinstance(development, list)
    assert development
    for requirement in development:
        assert "==" in requirement, requirement
        assert ">=" not in requirement, requirement
        assert "~=" not in requirement, requirement


def test_the_makefile_never_invokes_a_tool_from_path() -> None:
    """A bare `ruff`/`mypy`/`pytest` can resolve to a different environment.

    A globally installed, isolated mypy cannot see pytest or hypothesis and
    type-checks the suite against imports it cannot resolve. Going through the
    interpreter is what makes the toolchain and the package the same
    environment, so the Makefile must not regress to bare invocations.
    """
    makefile = (REPOSITORY / "Makefile").read_text(encoding="utf-8")
    continuation = False
    commands: list[str] = []
    for line in makefile.splitlines():
        if not line.startswith("\t"):
            continuation = False
            continue
        if not continuation:
            commands.append(line.lstrip("\t").split()[0])
        # A recipe line ending in a backslash continues into the next one,
        # which is an argument rather than a command.
        continuation = line.rstrip().endswith("\\")
    assert commands, "no recipe commands found in the Makefile"
    for command in commands:
        assert command == "$(PYTHON)", command


def test_the_supported_python_version_is_declared() -> None:
    assert _project_table()["requires-python"] == ">=3.11"


def test_the_package_declares_one_version_source() -> None:
    project = _project_table()
    assert project["dynamic"] == ["version"]
    assert "version" not in project
