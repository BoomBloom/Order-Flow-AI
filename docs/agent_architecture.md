# Agent Architecture

Status: **proposed, pre-implementation.** No agent may be built before the
deterministic layers it depends on exist (see `docs/roadmap.md`).

**Roster decision (architecture gate):** three active agent types, plus a
deferred Orchestrator. The former Market Structure, Order Flow, and Liquidity
agents are collapsed into a single **Feature Specification Agent** carrying
three versioned domain profiles.

---

## 1. Position of the agent layer

Agents sit **above** the deterministic engine. They read artifacts and write
proposals. They never appear in the hot path:

```
MARKET EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER     [no agent, ever]
```

A CI import check asserts that nothing under `features/`, `strategy/`,
`sim/`, or `context/` imports `agents/` `[ENFORCED]`.

What agents may produce: research summaries, operational definitions,
candidate hypotheses, feature specifications, context-rule specifications,
critiques, prioritized next experiments.

What agents may never produce: feature values, signals, orders, backtest
numbers, statistics, validation verdicts, or a trade decision of any kind.

An agent proposal only becomes real when it is compiled into a versioned
deterministic artifact (a feature module, a strategy spec, an experiment
record) that a human approves and code executes.

---

## 2. Roster

| Agent | Status | Phase |
| --- | --- | --- |
| Research Agent | Active | 8 |
| Feature Specification Agent (3 profiles) | Active | 8 |
| Adversarial Agent | Active | 8 |
| Orchestrator | **Deferred** | Not before 10, and only on evidence |

### 2.1 Why the three domain agents became one

Market Structure, Order Flow, and Liquidity were specified as three agents.
Under the Agent Existence Test they emit the same schema (`FeatureSpec`),
perform the same task shape (turn an ambiguous concept into an operational
definition), and consume the same kind of input. They differ only in domain
knowledge and data-capability constraints.

Question 5 — "what breaks if we delete it?" — has no convincing answer for
any one of them individually: delete the Liquidity Agent, and the same agent
running a liquidity knowledge pack does the identical job. **A domain
difference is a profile, not an agent boundary.**

The collapse loses nothing that matters: each profile keeps its own domain
knowledge, prompt instructions, capability constraints, and version. It gains
a single contract, a single output schema, one place to fix a specification
bug, and one fewer coordination surface.

### 2.2 Why the Orchestrator is deferred

The Orchestrator passes questions 1–4 of the Existence Test — decomposing an
open-ended research question is genuine reasoning. It fails on timing and
evidence.

With a handful of experiments, the human researcher *is* the orchestrator,
and the registry query CLI supplies the prior-work lookup that was the
Orchestrator's most valuable step. Building it early risks the worst outcome
in this design: a prose-generating middleman between a human and a
deterministic engine, adding cost and latency while obscuring who decided
what.

**Deferral condition.** The Orchestrator is built only when all hold:

1. The deterministic research loop is operational end to end (Phase 9
   complete).
2. Enough experiments exist that manual prior-work lookup and prioritization
   are demonstrably a bottleneck.
3. A written comparison shows what it would do beyond the documented human
   workflow plus the registry CLI.

Until then, `docs/research_protocol.md` §13 assigns the orchestration role to
the human researcher, and the workflow in §4 below is executed manually.

---

## 3. The Agent Existence Test

### Research Agent

1. **Why not deterministic?** Surveying literature and competing definitions
   and grading evidence strength is natural-language work.
2. **Reasoning:** synthesis, evidence grading, hypothesis generation.
3. **Unique input:** external literature and documentation; the registry of
   prior definitions and failures.
4. **Typed output:** `EvidenceSummary`, `DefinitionCandidate[]`,
   `HypothesisSpec[]`.
5. **If deleted:** hypotheses come from folklore; the same idea is retested
   under new names.

### Feature Specification Agent

1. **Why not deterministic?** The *computation* is deterministic and lives in
   `features/`. The specification act is not: choosing among defensible
   definitions (which value-area algorithm; what window, threshold, reference
   price, aggressor direction, persistence, and noise tolerance make
   "absorption" measurable), and stating the trade-offs and failure modes.
2. **Reasoning:** operationalizing ambiguous concepts; specifying edge cases,
   gap/reset behaviour, and roll policy; naming confounders and limits.
3. **Unique input:** the hypothesis's structural, flow, or book requirements,
   plus the data capability matrix and per-partition capability records.
4. **Typed output:** `FeatureSpec`, `ContextRuleSpec`.
5. **If deleted:** definitions get chosen implicitly by whoever writes the
   code first, undocumented, and subjective language leaks into strategies.

### Adversarial Agent

1. **Why not deterministic?** The verdict *is* deterministic. The agent
   supplies what a checklist cannot: proposing the specific attack this
   strategy invites, and naming the strongest argument against a result.
2. **Reasoning:** adversarial critique, alternative-explanation generation,
   next-test design.
3. **Unique input:** the verdict object, the registry's multiple-testing
   history including the self-reported discovery search log, and the
   experiment's own definition.
4. **Typed output:** `AdversarialReview`.
5. **If deleted:** nobody is structurally assigned to attack the result, and
   the researcher grades their own homework.

**No new agent** — and no split of an existing one — is created without
answering these five questions in a PR that also updates this document. A
domain difference is answered with a profile. Candidates deferred by design:
Orchestrator, Data Quality, Strategy Engineer, Statistical Analyst, Execution
Research, Risk, Literature, Portfolio, Options/GEX. Each is currently a
deterministic module or a human responsibility; that is the correct default.

---

## 4. Feature Specification Agent — domain profiles

One agent type, one output schema, three versioned profiles. A profile is
data: a prompt module, a domain knowledge document, capability constraints,
and a version. Profiles are selected per task and recorded in the run log.

```
FeatureSpecificationAgent
  profile: market_structure @ <version>
  profile: order_flow       @ <version>
  profile: liquidity        @ <version>
```

### 4.1 `market_structure`

**Scope:** Market Profile, Volume Profile, POC, VAH, VAL, HVN, LVN,
volume-at-price, Initial Balance, Opening Range, value migration, balance and
imbalance, acceptance and rejection, session structure, prior-session
references.

**Capability constraints:** trades at minimum; TPO structure requires either
trades or 30-minute bars. Does not require book data.

**Profile-specific obligations:** never uses visual or discretionary language
without an operational definition; specifies mathematical definition, input
events, lookback, session, timezone, output units, edge cases, and tests;
must state the `prior_session.*` versus `developing.*` form of every
session-derived value; must declare `roll_policy` — price-level state is
`RESET`; may propose `ContextRuleSpec` values (`BALANCED`, `IMBALANCED`,
`BREAKOUT_ATTEMPT`, `ACCEPTANCE`, `REJECTION`, `ROTATION`, `TRENDING`), each
mapping to deterministic rules.

**Known definitional conflicts it must preserve rather than resolve
silently:** value-area construction has several incompatible standard
definitions; competing candidates are recorded, not merged.

### 4.2 `order_flow`

**Scope:** bid/ask volume, delta, delta rate, CVD, footprint imbalance,
stacked imbalance, aggression, absorption, exhaustion, failed continuation,
trade velocity, trade-size behaviour.

**Capability constraints:** trades plus aggressor side. Must declare the
minimum acceptable provenance tier for aggressor side and specify behaviour
when it is `INFERRED` or `UNKNOWN`, including how excluded volume is
reported.

**Profile-specific obligations:** no order-flow term may remain subjective.
"Absorption" may not mean "large buying but price does not rise"; it must
define time/event window, executed-volume threshold, price-displacement
threshold, reference price, aggressor direction, persistence, and noise
tolerance. Every proposed feature delivers: definition, formula/pseudocode,
required data, parameters, edge cases, gap/reset behaviour, failure modes,
unit tests, interpretation limits.

**Prohibition:** never label an event predictive until it has been
empirically tested.

### 4.3 `liquidity`

**Scope:** depth, depth imbalance, liquidity concentration, liquidity change,
withdrawal, replenishment, stacking, pulling, sweeps, resting liquidity,
liquidity migration, book pressure, and the interaction between aggressive
execution and resting liquidity.

**Capability constraints:** MBP-10 at minimum; queue-level work requires MBO.
Must state required feed granularity per feature and mark as blocked anything
the target instrument's capability record cannot support.

**Profile-specific obligations:** order-book state is time-dependent — a
single snapshot is never treated as representative; measure transitions
`STATE(t) -> STATE(t + Δt)`. Strictly separate resting liquidity, executed
volume, cancelled liquidity, added liquidity, replenished liquidity, and
aggressive market orders. Never infer intent from the presence of a large
order. Every spec states aggregation method, event timing, limitations, and
likely confounders.

**Provenance obligation:** sweep and pulling classifications are `INFERRED`,
not `RECONSTRUCTED`, and must be labelled as such. Queue position is
`SIMULATED` and is never proposed as a feature input.

---

## 5. Typed contracts

Agents communicate through versioned schemas, never free prose. Every agent
output carries an envelope:

```json
{
  "schema": "ofa.agents.FeatureSpec",
  "schema_version": "1.0.0",
  "run_id": "...", "parent_run_id": "...",
  "agent": "feature_specification",
  "profile": {"name": "order_flow", "version": "1.2.0"},
  "model": "...", "prompt_version": "...",
  "input_versions": {"registry": "...", "dataset": "...", "task": "..."},
  "created_at": "...",
  "payload": { "...": "..." },
  "confidence": {"level": "PLAUSIBLE", "rationale": "..."},
  "open_questions": ["..."]
}
```

Rules:

- Every payload validates against its schema or the run fails. Pydantic is
  used here — this is a boundary, not a hot path.
- `confidence.level` uses the fixed vocabulary `ESTABLISHED | SUPPORTED |
  PLAUSIBLE | SPECULATIVE | UNKNOWN`.
- No payload field may contain a number that deterministic code owns
  (feature values, PnL, statistics). Proposed *parameter defaults* are
  allowed and are explicitly labelled as proposals.
- Every `FeatureSpec` payload must declare `requires`, minimum provenance
  tier, `lookback`, `roll_policy`, and gap/reset behaviour — a spec missing
  these cannot be compiled into a feature.
- Outputs are immutable once written and are stored in the registry.

Core schemas: `ResearchTask`, `EvidenceSummary`, `DefinitionCandidate`,
`HypothesisSpec`, `FeatureSpec`, `ContextRuleSpec`, `StrategySpecProposal`,
`AdversarialReview`, `ConflictReport`. `ResearchPlan` is defined but unused
until the Orchestrator is built.

---

## 6. Workflow (human-orchestrated until §2.2 is satisfied)

1. Receive a research question or an experiment follow-up.
2. Classify it: conceptual, data, feature, hypothesis, backtest, validation.
3. **Query the registry for prior work on the same concept and hypothesis
   family — mandatory, before any agent call.**
4. Assign tasks with explicit acceptance criteria.
5. Dispatch to the Research Agent and/or the Feature Specification Agent with
   the appropriate profile; collect typed outputs.
6. Detect conflicts.
7. Formalize a `HypothesisSpec`, including split policy and thresholds.
8. Request deterministic implementation (human-approved).
9. Trigger the backtest.
10. Trigger validation.
11. Store results and lineage.
12. Decide the next experiment.

**Conflict rule:** disagreement — between two agent outputs, two profiles, or
an agent and a stored result — is never resolved by voting or averaging.
Preserve both definitions, record why they differ, and where possible test
them as separate experiments. A `ConflictReport` is a first-class artifact.

**Hard prohibitions** (applying to whoever performs the orchestration role,
human or, later, agent): may not modify numerical results, declare a strategy
profitable on judgement, emit a BUY/SELL decision, or skip the registry
lookup in step 3.

---

## 7. Human-in-the-loop checkpoints

Mandatory human approval before: implementing a proposed feature; freezing a
strategy definition; touching the confirmation segment; touching the holdout;
any status transition into `VALIDATED` or `PAPER_TRADING`.

Agents may run freely up to those points.

---

## 8. Model routing

| Role | Used for | Notes |
| --- | --- | --- |
| Strategic | Architecture decisions, research programme design | Strongest model, rarely invoked |
| Synthesis | Hypothesis generation, evidence summaries | Strong model |
| Adversarial | Validation critique | Strong model; deliberately a *different* invocation from the one that generated the hypothesis |
| Implementation | Routine code and test generation | Mid-tier |
| Classification | Structured labelling, tagging, dedup candidates | Cheapest capable model |

Deterministic quantitative calculations call no model. Model choice, prompt
version, profile version, token usage, and cost are recorded per run.

---

## 9. Observability

Every agent run records: run ID, parent run ID, agent, **profile and profile
version**, model, prompt version, input versions, output artifact ID,
latency, token usage, cost, status, errors, and retries. Agent runs are
queryable alongside deterministic runs so a conclusion's full provenance
includes which model and which profile said what, when, and at what cost.

---

## 10. Failure and degradation

- Schema validation failure: reject the output, retry once with the
  validation error, then fail the task. Never accept malformed output.
- Model unavailable: the task fails and is queued; the deterministic pipeline
  continues unaffected. No part of the research loop may block on model
  availability.
- Agent proposes a feature requiring unavailable data: the proposal is
  recorded as blocked with the minimum additional data required, per the
  capability matrix. It is not approximated.
- Agent contradicts a stored result: the stored result wins; the
  contradiction is logged as a `ConflictReport` for human review.
