"""Provenance tiers: how a quantity came to be known.

``docs/data_specification.md`` section 2 defines four tiers and, just as
importantly, the rules that keep them apart:

* ``OBSERVED`` — present in the vendor feed as delivered.
* ``RECONSTRUCTED`` — deterministically derived from observed data, with no
  free parameters and no counterfactual.
* ``INFERRED`` — derived by a heuristic that has a non-zero error rate.
* ``SIMULATED`` — counterfactual: it describes a hypothetical order of ours
  that never existed.

``INFERRED`` is **not** a lossy ``RECONSTRUCTED``. Reconstruction is exact;
inference can be wrong. The specification forbids merging them into one value
or one confidence label, and this module keeps them distinct members rather
than points on a confidence scale.

The order is partial, not total
-------------------------------

The three *data* tiers are ordered by strength::

    OBSERVED  >  RECONSTRUCTED  >  INFERRED

``SIMULATED`` sits outside that order entirely. It is not a weaker
``INFERRED``: it is not a claim about the market at all, so it is neither
stronger nor weaker than a claim that is. Asking whether it satisfies a
market-data requirement raises ``IncomparableProvenanceError`` rather than
answering ``False``, because ``False`` would be read as a missing feed when
the real fault is that simulated output was offered as input data.

Because the order is partial, this module deliberately defines **no**
comparison operators. ``<`` and ``>`` advertise a total order, and a total
order over these four members does not exist. Admissibility is asked for by
name, through :meth:`ProvenanceTier.satisfies`, where the question and its
failure mode are both visible at the call site.

``SIMULATED`` may still be *recorded*. ``docs/data_specification.md`` section
2 requires every derived quantity to resolve to exactly one tier in a
manifest, and fills, slippage and queue position are always ``SIMULATED``. So
it is representable in a run's provenance data; what it can never do is
satisfy a feature's data requirement.
"""

from __future__ import annotations

from enum import Enum
from typing import Final

from ofa.core.errors import IncomparableProvenanceError, ProvenanceTypeError


class ProvenanceTier(Enum):
    """How a quantity came to be known.

    The member *name* is the identity, and it is what the canonical form
    hashes and what a manifest records (``"tier": "OBSERVED"``). Each value is
    its own name so that the two can never drift apart.
    """

    OBSERVED = "OBSERVED"
    RECONSTRUCTED = "RECONSTRUCTED"
    INFERRED = "INFERRED"
    SIMULATED = "SIMULATED"

    def satisfies(self, minimum: ProvenanceTier) -> bool:
        """Whether this tier is at least as strong as ``minimum``.

        Both sides must be data tiers. ``SIMULATED`` on either side raises
        ``IncomparableProvenanceError``: it is outside the order, and a
        counterfactual can neither meet nor set a bar for observed reality.

        This is the check behind the specification's ``[ENFORCED]`` rule that
        a run supplying a weaker tier than a feature declared acceptable fails
        rather than degrading silently.
        """
        if not isinstance(minimum, ProvenanceTier):
            raise ProvenanceTypeError(
                f"minimum tier must be a ProvenanceTier, not {type(minimum).__name__}"
            )
        for tier, role in ((self, "supplied"), (minimum, "required")):
            if tier is ProvenanceTier.SIMULATED:
                raise IncomparableProvenanceError(
                    f"SIMULATED is outside the data-tier order and cannot be the "
                    f"{role} tier of an admissibility check; it describes a "
                    f"hypothetical order of ours, not an observation of the market"
                )
        return _DATA_TIER_RANK[self] >= _DATA_TIER_RANK[minimum]


#: Strength of each data tier. Private: the numbers order the three data tiers
#: and nothing else. They are never serialized, never hashed — the canonical
#: form uses the member name — and ``SIMULATED`` is deliberately absent, so a
#: lookup for it raises rather than placing it in an order it does not belong
#: to.
_DATA_TIER_RANK: Final[dict[ProvenanceTier, int]] = {
    ProvenanceTier.INFERRED: 1,
    ProvenanceTier.RECONSTRUCTED: 2,
    ProvenanceTier.OBSERVED: 3,
}
