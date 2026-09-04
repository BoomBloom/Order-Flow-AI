"""Property tests for canonical serialization and stable content hashing.

No float appears in any strategy. The exact domain has no float path, and
generating one here would only ever assert that it is rejected — which the
example-based tests already do precisely.
"""

from __future__ import annotations

import copy
import json
import re
from typing import Final

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from ofa.core.hashing import canonical_bytes, content_hash, params_hash
from ofa.core.money import INT64_MAX, INT64_MIN, Price, Ticks
from ofa.core.time import TradeDate, UtcNanos

int64s = st.integers(min_value=INT64_MIN, max_value=INT64_MAX)

trade_dates = st.dates().map(lambda d: TradeDate(d.year, d.month, d.day))

#: Every leaf the canonicalizer accepts. Hypothesis excludes surrogates from
#: st.text() by default, which is what the canonical form also requires.
leaves: Final[st.SearchStrategy[object]] = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.text(max_size=8),
    st.binary(max_size=8),
    int64s.map(Price),
    int64s.map(Ticks),
    int64s.map(UtcNanos),
    trade_dates,
)

keys = st.text(max_size=6)

canonical_values: Final[st.SearchStrategy[object]] = st.recursive(
    leaves,
    lambda children: st.one_of(
        st.lists(children, max_size=4),
        st.lists(children, max_size=4).map(tuple),
        st.dictionaries(keys, children, max_size=4),
    ),
    max_leaves=10,
)

canonical_mappings: Final[st.SearchStrategy[dict[str, object]]] = st.dictionaries(
    keys, canonical_values, max_size=5
)

HEX_DIGEST = re.compile(r"\A[0-9a-f]{64}\Z")

# Hypothesis regenerates the recursive strategy per example; the default
# data-generation deadline is not a meaningful signal here.
relaxed = settings(suppress_health_check=[HealthCheck.too_slow], deadline=None)


def _as_lists(value: object) -> object:
    """Collapse tuples to lists, so equality means *canonical* equality.

    A tuple and a list with the same contents are unequal in Python but share
    one canonical tag by design, so a raw ``!=`` is not the right predicate for
    "these should hash differently".
    """
    if isinstance(value, (list, tuple)):
        return [_as_lists(item) for item in value]
    if isinstance(value, dict):
        return {key: _as_lists(item) for key, item in value.items()}
    return value


@given(canonical_values)
@relaxed
def test_canonical_bytes_are_deterministic(value: object) -> None:
    assert canonical_bytes(value) == canonical_bytes(value)


@given(canonical_values)
@relaxed
def test_canonical_bytes_are_pure_ascii(value: object) -> None:
    canonical_bytes(value).decode("ascii")


@given(canonical_values)
@relaxed
def test_rendering_is_exactly_the_compact_form(value: object) -> None:
    """Re-rendering the parsed node compactly reproduces the bytes exactly.

    This is the separator property stated so that it survives strings which
    legitimately contain spaces: whitespace inside a string literal is content,
    whitespace between structural tokens is drift.
    """
    produced = canonical_bytes(value)
    reparsed = json.loads(produced)
    recompacted = json.dumps(reparsed, ensure_ascii=True, separators=(",", ":"))
    assert recompacted.encode("ascii") == produced


@given(canonical_values)
@relaxed
def test_digest_is_sixty_four_lowercase_hex_characters(value: object) -> None:
    assert HEX_DIGEST.fullmatch(content_hash(value))


@given(canonical_values)
@relaxed
def test_equal_but_distinct_objects_produce_identical_output(value: object) -> None:
    duplicate = copy.deepcopy(value)
    assert canonical_bytes(duplicate) == canonical_bytes(value)
    assert content_hash(duplicate) == content_hash(value)


@given(canonical_mappings, st.data())
@relaxed
def test_mapping_key_insertion_order_never_matters(
    mapping: dict[str, object], data: st.DataObject
) -> None:
    shuffled_items = data.draw(st.permutations(list(mapping.items())))
    rebuilt = dict(shuffled_items)
    assert rebuilt.keys() == mapping.keys()
    assert canonical_bytes(rebuilt) == canonical_bytes(mapping)
    assert content_hash(rebuilt) == content_hash(mapping)


@given(canonical_values, canonical_values)
@relaxed
def test_different_values_produce_different_digests(left: object, right: object) -> None:
    if _as_lists(left) == _as_lists(right):
        return
    assert canonical_bytes(left) != canonical_bytes(right)
    assert content_hash(left) != content_hash(right)


@given(canonical_values, canonical_values)
@relaxed
def test_equal_values_produce_equal_digests(left: object, right: object) -> None:
    if _as_lists(left) != _as_lists(right):
        return
    assert canonical_bytes(left) == canonical_bytes(right)
    assert content_hash(left) == content_hash(right)


@given(canonical_mappings, keys, canonical_values)
@relaxed
def test_adding_a_parameter_changes_the_digest(
    mapping: dict[str, object], key: str, value: object
) -> None:
    if key in mapping:
        return
    extended = {**mapping, key: value}
    assert content_hash(extended) != content_hash(mapping)


@given(canonical_mappings)
@relaxed
def test_params_hash_agrees_with_content_hash(mapping: dict[str, object]) -> None:
    assert params_hash(mapping) == content_hash(mapping)


@given(int64s)
def test_price_ticks_and_instant_never_share_a_canonical_form(value: int) -> None:
    forms = {
        canonical_bytes(Price(value)),
        canonical_bytes(Ticks(value)),
        canonical_bytes(UtcNanos(value)),
        canonical_bytes(value),
    }
    assert len(forms) == 4


@given(trade_dates)
def test_trade_date_canonical_form_is_its_iso_string(value: TradeDate) -> None:
    assert canonical_bytes(value) == f'["trade_date","{value.isoformat()}"]'.encode("ascii")
    assert canonical_bytes(value) != canonical_bytes(value.isoformat())
