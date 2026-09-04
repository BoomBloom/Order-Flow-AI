"""Example-based tests for the ``ofa`` command.

The output of ``ofa version`` is a contract, not a convenience, so it is
asserted structurally rather than by eyeball.
"""

from __future__ import annotations

import ast
import json
from importlib import import_module

import pytest

from ofa.cli.main import main
from ofa.core.versioning import SCHEMA_VERSIONS, render_version_report

# The package re-exports the `main` function, which shadows the submodule of
# the same name, so the module is imported explicitly rather than by attribute.
cli_module = import_module("ofa.cli.main")


def test_version_prints_the_report_and_succeeds(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["version"]) == 0
    captured = capsys.readouterr()
    assert captured.out == render_version_report()
    assert captured.err == ""


def test_version_output_is_parseable_json(capsys: pytest.CaptureFixture[str]) -> None:
    main(["version"])
    parsed = json.loads(capsys.readouterr().out)
    assert set(parsed) == {"package", "code_revision", "schema_versions"}
    assert parsed["schema_versions"] == dict(SCHEMA_VERSIONS)


def test_version_output_is_identical_on_repeated_invocations(
    capsys: pytest.CaptureFixture[str],
) -> None:
    main(["version"])
    first = capsys.readouterr().out
    main(["version"])
    assert capsys.readouterr().out == first


def test_no_command_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert main([]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "usage: ofa" in captured.err
    assert "ofa version" in captured.err


def test_an_unknown_command_is_rejected() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["bogus"])
    assert caught.value.code == 2


def test_help_exits_cleanly(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--help"])
    assert caught.value.code == 0
    assert "version" in capsys.readouterr().out


def test_version_help_exits_cleanly() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["version", "--help"])
    assert caught.value.code == 0


def test_version_takes_no_options() -> None:
    """The surface stays minimal: no flags to drift into a configuration API."""
    for option in (["version", "--json"], ["version", "--short"], ["version", "x"]):
        with pytest.raises(SystemExit) as caught:
            main(option)
        assert caught.value.code == 2


def test_the_only_subcommand_is_version() -> None:
    """Asserted behaviourally: `version` parses, and nothing else does."""
    parser = cli_module._build_parser()
    assert parser.parse_args(["version"]).command == "version"
    candidates = [
        "run",
        "data",
        "backtest",
        "research",
        "config",
        "ingest",
        "replay",
        "validate",
        "shell",
        "status",
        "Version",
        "versions",
    ]
    for candidate in candidates:
        with pytest.raises(SystemExit):
            parser.parse_args([candidate])


def test_cli_declares_no_third_party_dependency() -> None:
    source_path = cli_module.__file__
    assert source_path is not None
    with open(source_path, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "argparse", "sys", "collections", "ofa"}


def test_version_help_mentions_the_command() -> None:
    """Phase 0 puts every other CLI command out of scope; help names only this one."""
    parser = cli_module._build_parser()
    help_text = parser.format_help()
    assert "ofa" in help_text
    assert "version" in help_text
