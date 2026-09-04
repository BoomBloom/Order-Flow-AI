"""Cross-process determinism: the Phase 0 exit criterion for stable hashing.

``docs/roadmap.md`` Phase 0 exit criterion 3 requires ``params_hash`` to be
byte-identical across two **separate interpreter processes**, specifically to
catch Python's salted ``hash()``. Every other test in the suite runs in one
process, where a salted hash is perfectly stable and therefore invisible.

The tests below spawn real interpreters under two different hash seeds. Each
subprocess also reports ``hash("abc")``, and the test asserts those two values
*differ* — without that check the whole exercise could pass while proving
nothing, because both children might have been given the same seed.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from collections.abc import Sequence
from enum import Enum
from typing import Final, cast

import ofa
from ofa.core.hashing import content_hash
from ofa.core.money import Price, Ticks
from ofa.core.time import TradeDate, UtcNanos

#: The importable source root, so the child interpreter can find the package
#: without depending on it being installed.
SRC: Final = pathlib.Path(ofa.__file__).resolve().parent.parent

#: Two pinned, distinct, non-zero seeds. Zero is not used: it *disables*
#: randomization rather than selecting a seed, so a pair including it would
#: test less than it appears to.
SEED_A: Final = "1"
SEED_B: Final = "12345"

# The child program. Raw, so escapes reach the child's parser rather than
# being resolved by this file's parser. It builds one non-trivial structure in
# a caller-chosen key order and reports what it produced.
_PROGRAM: Final = r"""
import json, sys
from enum import Enum

from ofa.core.hashing import canonical_bytes, content_hash, params_hash
from ofa.core.money import Price, Ticks
from ofa.core.time import TradeDate, UtcNanos


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


pairs = [
    ("zeta", "été 中文"),
    ("alpha", [1, -2, True, False, None]),
    ("nested", {"b": Price(1500000000), "a": Ticks(-6), "c": {"deep": (7, 8)}}),
    ("raw", b"\x00\xff\x10"),
    ("when", UtcNanos(-1)),
    ("day", TradeDate(2024, 3, 11)),
    ("side", Side.SELL),
    ("big", 2 ** 70),
]
if sys.argv[1] == "reversed":
    pairs = list(reversed(pairs))
payload = dict(pairs)

print(json.dumps({
    "hash_abc": hash("abc"),
    "canonical": canonical_bytes(payload).decode("ascii"),
    "content": content_hash(payload),
    "params": params_hash(payload),
}))
"""


def _run(seed: str, order: str, extra_args: Sequence[str] = ()) -> dict[str, object]:
    """Run the child program in a fresh interpreter under ``seed``."""
    env = {**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(SRC)}
    completed = subprocess.run(
        [sys.executable, *extra_args, "-c", _PROGRAM, order],
        env=env,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    result: dict[str, object] = json.loads(completed.stdout)
    return result


def test_two_processes_with_different_hash_seeds_agree() -> None:
    first = _run(SEED_A, "natural")
    second = _run(SEED_B, "natural")

    # The guard: prove the two interpreters really were seeded differently.
    # Without this the equality assertions below could be vacuous.
    assert first["hash_abc"] != second["hash_abc"]

    assert first["canonical"] == second["canonical"]
    assert first["content"] == second["content"]
    assert first["params"] == second["params"]


def test_key_insertion_order_does_not_survive_into_the_canonical_form() -> None:
    """Different seeds *and* different insertion order, same bytes."""
    natural = _run(SEED_A, "natural")
    reversed_order = _run(SEED_B, "reversed")

    assert natural["hash_abc"] != reversed_order["hash_abc"]
    assert natural["canonical"] == reversed_order["canonical"]
    assert natural["content"] == reversed_order["content"]


def test_forced_randomization_does_not_change_the_result() -> None:
    """PYTHONHASHSEED=random plus -R: randomization on, unseeded, twice."""
    first = _run("random", "natural", extra_args=["-R"])
    second = _run("random", "reversed", extra_args=["-R"])

    assert first["canonical"] == second["canonical"]
    assert first["content"] == second["content"]


def test_params_hash_equals_content_hash_across_processes() -> None:
    result = _run(SEED_A, "natural")
    assert result["params"] == result["content"]


def test_child_digest_matches_this_process() -> None:
    """The child's digest is reproducible here, not merely self-consistent."""
    # Rebuilt with the child's module name, so the enum tag matches the one
    # the child produced for its own module-level class.
    side = cast(
        "type[Enum]",
        Enum("Side", [("BUY", "buy"), ("SELL", "sell")], module="__main__"),
    )
    payload = {
        "zeta": "été 中文",
        "alpha": [1, -2, True, False, None],
        "nested": {"b": Price(1500000000), "a": Ticks(-6), "c": {"deep": (7, 8)}},
        "raw": b"\x00\xff\x10",
        "when": UtcNanos(-1),
        "day": TradeDate(2024, 3, 11),
        "side": side["SELL"],
        "big": 2**70,
    }
    assert _run(SEED_A, "natural")["content"] == content_hash(payload)
