"""State-lifecycle enums for streaming computation.

Two vocabularies that the architecture already fixes, declared here as
standalone value types. They are the answers to "what happens to accumulated
state when the world changes underneath it".

They are deliberately **not** accompanied by the ``Feature`` protocol. That
protocol names five further types — ``FeatureParams``, ``Lookback``,
``StreamGap``, ``FeatureUpdate`` and ``FeatureState`` — which appear nowhere
in the specification except as names, and ``Lookback`` carries an unresolved
conflict between event-count, volume, time and session windows. Declaring
these two enums now costs nothing and pulls nothing forward; inventing the
other five to make a signature type-check would be designing the feature
engine by accident, and ``docs/architecture.md`` section 16 item 2 makes that
expensive to undo.
"""

from __future__ import annotations

from enum import Enum


class RollPolicy(Enum):
    """What a stateful feature does with its state at a contract roll.

    ``docs/architecture.md`` section 5.1: a feature carrying state across a
    roll would be mixing two instruments, so every stateful feature declares a
    policy and **there is no default**.
    """

    #: State is discarded at the roll boundary and warm-up restarts. The
    #: expected policy for anything price-level — profile, VWAP, POC/VAH/VAL,
    #: anchored VWAP. A feature specifying CARRY for price-level state fails
    #: review.
    RESET = "RESET"

    #: State persists across the roll. Legitimate only for instrument-agnostic
    #: state, such as trade-count rates or time-of-day counters.
    CARRY = "CARRY"

    #: State persists with an explicit, versioned price adjustment applied.
    #: Requires written justification, and the adjustment is recorded in the
    #: feature manifest.
    CARRY_ADJUSTED = "CARRY_ADJUSTED"


class ResetReason(Enum):
    """Why accumulated state must be discarded.

    ``docs/architecture.md`` section 6.2. The reason is passed to the feature
    rather than inferred by it, so that replay and live are indistinguishable
    from inside a feature — which is what makes the paper-trading divergence
    alarm meaningful.
    """

    #: A new trading session began.
    SESSION_START = "SESSION_START"

    #: The contract rolled and the declared roll policy is RESET.
    CONTRACT_ROLL = "CONTRACT_ROLL"

    #: A split segment began. The runner issues this at every segment
    #: boundary, then replays the burn-in window before signals are honoured,
    #: so that a feature warmed on discovery data cannot carry that state into
    #: confirmation (``docs/research_protocol.md`` section 4.3).
    SPLIT_SEGMENT_START = "SPLIT_SEGMENT_START"

    #: Trading resumed after a halt.
    HALT_RESUME = "HALT_RESUME"

    #: A live feed disconnected and resumed.
    LIVE_RECONNECT = "LIVE_RECONNECT"
