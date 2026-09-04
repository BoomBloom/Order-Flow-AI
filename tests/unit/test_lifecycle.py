"""Example-based tests for the state-lifecycle enums."""

from __future__ import annotations

import ast
import operator

import pytest

from ofa.core import lifecycle
from ofa.core.lifecycle import ResetReason, RollPolicy


def test_roll_policies_are_exactly_those_the_architecture_names() -> None:
    assert [policy.name for policy in RollPolicy] == ["RESET", "CARRY", "CARRY_ADJUSTED"]


def test_reset_reasons_are_exactly_those_the_architecture_names() -> None:
    assert [reason.name for reason in ResetReason] == [
        "SESSION_START",
        "CONTRACT_ROLL",
        "SPLIT_SEGMENT_START",
        "HALT_RESUME",
        "LIVE_RECONNECT",
    ]


@pytest.mark.parametrize("enumeration", [RollPolicy, ResetReason])
def test_each_value_is_its_own_name(enumeration: type) -> None:
    for member in enumeration:  # type: ignore[attr-defined]
        assert member.value == member.name


@pytest.mark.parametrize("enumeration", [RollPolicy, ResetReason])
def test_members_are_not_integers(enumeration: type) -> None:
    for member in enumeration:  # type: ignore[attr-defined]
        assert not isinstance(member, int)


@pytest.mark.parametrize("enumeration", [RollPolicy, ResetReason])
def test_there_is_no_default_member(enumeration: type) -> None:
    """architecture.md section 5.1: every stateful feature declares a policy."""
    for name in ("DEFAULT", "NONE", "UNKNOWN", "UNSPECIFIED"):
        assert name not in enumeration.__members__  # type: ignore[attr-defined]


@pytest.mark.parametrize("enumeration", [RollPolicy, ResetReason])
def test_members_are_not_orderable(enumeration: type) -> None:
    members = list(enumeration)  # type: ignore[call-overload]
    for operation in (operator.lt, operator.le, operator.gt, operator.ge):
        with pytest.raises(TypeError):
            operation(members[0], members[1])


def test_the_two_enumerations_never_compare_equal() -> None:
    """mypy rejects both comparisons as non-overlapping; runtime agrees."""
    assert RollPolicy.RESET != ResetReason.SESSION_START  # type: ignore[comparison-overlap]
    assert (
        RollPolicy.RESET.value  # type: ignore[comparison-overlap]
        != ResetReason.SESSION_START.value
    )


def test_lifecycle_module_pulls_no_feature_machinery_forward() -> None:
    """The five undefined Feature types must not appear here."""
    with open(lifecycle.__file__, encoding="utf-8") as handle:
        tree = ast.parse(handle.read())
    defined = {
        node.name for node in ast.walk(tree) if isinstance(node, (ast.ClassDef, ast.FunctionDef))
    }
    assert defined == {"RollPolicy", "ResetReason"}
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "enum"}
