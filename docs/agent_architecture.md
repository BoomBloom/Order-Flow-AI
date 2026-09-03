# Agent Architecture

Status: **proposed, pre-implementation.** No agent may be built before the
deterministic layers it depends on exist (see `docs/roadmap.md`).

---

## 1. Position of the agent layer

Agents sit **above** the deterministic engine. They read artifacts and write
proposals. They never appear in the hot path:

```
MARKET EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER     [no agent, ever]
```

What agents may produce: research summaries, operational definitions,
candidate hypotheses, feature specifications, context-rule specifications,
critiques, prioritized next experiments.

What agents may never produce: feature values, signals, orders, backtest
numbers, statistics, validation verdicts, or a trade decision of any kind.

An agent proposal only becomes real when it is compiled into a versioned
deterministic artifact (a feature module, a strategy spec, an experiment
record) that a human approves and code executes.

---

## 2. The Agent Existence Test

Every agent — existing or proposed — must answer these five questions in this
document. If it cannot, delete it.

### Orchestrator

1. **Why not deterministic?** Decomposing an open-ended research question
   into tasks, and deciding what to test next given a body of prior results,
   is not expressible as a rule table.
2. **Reasoning performed:** decomposition, delegation, conflict detection,
   prioritization.
3. **Unique input:** the user's research question plus the full registry
   state.
4. **Typed output:** `ResearchPlan` (ordered `ResearchTask` objects with
   assigned agent, inputs, expected output, dependencies, acceptance
   criteria).
5. **If deleted:** every agent invocation becomes manual; conflicts between
   agent outputs go unnoticed; no prioritization of the experiment queue.

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

### Market Structure Agent

1. **Why not deterministic?** The *computation* is deterministic and lives in
   `features/profile`. The agent's job is choosing among defensible
   definitions (which value-area algorithm, which IB window, what
   "acceptance" means here) and stating the trade-offs.
2. **Reasoning:** operationalizing auction concepts; specifying edge cases.
3. **Unique input:** structural context requirements of a hypothesis.
4. **Typed output:** `FeatureSpec` (profile/market-structure family),
   `ContextRuleSpec`.
5. **If deleted:** definitions get chosen implicitly by whoever writes the
   code first, undocumented.

### Order Flow Agent

1. **Why not deterministic?** Same shape: turning "absorption" into a
   measurable event with window, thresholds, reference price, aggressor
   direction, persistence, and noise tolerance is a specification act.
2. **Reasoning:** formalizing ambiguous flow concepts; naming failure modes.
3. **Unique input:** flow-related hypothesis requirements; data capability
   constraints.
4. **Typed output:** `FeatureSpec` (order-flow family) including formula,
   parameters, edge cases, failure modes, and required unit tests.
5. **If deleted:** subjective flow language leaks into strategies.

### Liquidity Agent

1. **Why not deterministic?** Book-behaviour concepts (pulling, stacking,
   replenishment, sweeps) depend on feed granularity and require explicit
   modelling choices and stated limitations.
2. **Reasoning:** specifying state-transition measurements `STATE(t) ->
   STATE(t+Δt)`; distinguishing resting, executed, cancelled, added, and
   replenished liquidity; naming confounders.
3. **Unique input:** book-data capability matrix; liquidity hypothesis
   requirements.
4. **Typed output:** `FeatureSpec` (liquidity family) plus required feed
   granularity and limitations.
5. **If deleted:** book features get built on snapshot assumptions that do
   not hold, and intent gets inferred from the presence of a large order.

### Validation / Adversarial Agent

1. **Why not deterministic?** The verdict *is* deterministic. The agent
   supplies what a checklist cannot: proposing the specific attack this
   strategy invites, and naming the strongest argument against a result.
2. **Reasoning:** adversarial critique, alternative-explanation generation,
   next-test design.
3. **Unique input:** the verdict object, the registry's multiple-testing
   history, and the experiment's own definition.
4. **Typed output:** `AdversarialReview` (evidence against, evidence for,
   remaining uncertainty, required next experiment, requested additional
   tests).
5. **If deleted:** nobody is structurally assigned to attack the result, and
   the researcher grades their own homework.

**No seventh agent** is created without answering these five questions in a
PR that also updates this document. Candidates deferred by design: Data
Quality, Strategy Engineer, Statistical Analyst, Execution Research, Risk,
Literature, Portfolio, Options/GEX. Each is currently a deterministic module
or a human responsibility; that is the correct default.

---

## 3. Typed contracts

Agents communicate through versioned schemas, never free prose. Every agent
output carries an envelope:

```json
{
  "schema": "ofa.agents.FeatureSpec",
  "schema_version": "1.0.0",
  "run_id": "...", "parent_run_id": "...",
  "agent": "order_flow", "model": "...", "prompt_version": "...",
  "input_versions": {"registry": "...", "dataset": "...", "task": "..."},
  "created_at": "...",
  "payload": { "...": "..." },
  "confidence": {"level": "PLAUSIBLE", "rationale": "..."},
  "open_questions": ["..."]
}
```

Rules:

- Every payload validates against its schema or the run fails.
- `confidence.level` uses the fixed vocabulary `ESTABLISHED | SUPPORTED |
  PLAUSIBLE | SPECULATIVE | UNKNOWN`.
- No payload field may contain a number that deterministic code owns
  (feature values, PnL, statistics). Proposed *parameter defaults* are
  allowed and are explicitly labelled as proposals.
- Outputs are immutable once written and are stored in the registry.

Core schemas: `ResearchTask`, `ResearchPlan`, `EvidenceSummary`,
`DefinitionCandidate`, `HypothesisSpec`, `FeatureSpec`, `ContextRuleSpec`,
`StrategySpecProposal`, `AdversarialReview`, `ConflictReport`.

---

## 4. Orchestration

Workflow:

1. Receive a research question or an experiment follow-up.
2. Classify it: conceptual, data, feature, hypothesis, backtest, validation.
3. Query the registry for prior work on the same concept (mandatory — before
   any agent call).
4. Build a `ResearchPlan` with acceptance criteria per task.
5. Dispatch tasks to agents; collect typed outputs.
6. Detect conflicts.
7. Formalize a `HypothesisSpec`.
8. Request deterministic implementation (human-approved).
9. Trigger the backtest.
10. Trigger validation.
11. Store results and lineage.
12. Recommend the next experiment.

**Conflict rule:** disagreement is never resolved by voting or averaging.
Preserve both definitions, record why they differ, and where possible test
them as separate experiments. A `ConflictReport` is a first-class artifact.

**Hard prohibitions:** the Orchestrator may not modify numerical results,
declare a strategy profitable on LLM judgement, emit a BUY/SELL decision, or
skip the registry lookup in step 3.

---

## 5. Human-in-the-loop checkpoints

Mandatory human approval before: implementing a proposed feature; freezing a
strategy definition; touching the confirmation sample; touching the holdout;
any status transition into `VALIDATED` or `PAPER_TRADING`.

Agents may run freely up to those points.

---

## 6. Model routing

| Role | Used for | Notes |
| --- | --- | --- |
| Strategic | Architecture decisions, research programme design | Strongest model, rarely invoked |
| Synthesis | Hypothesis generation, evidence summaries | Strong model |
| Adversarial | Validation critique | Strong model; deliberately a *different* invocation from the one that generated the hypothesis |
| Implementation | Routine code and test generation | Mid-tier |
| Classification | Structured labelling, tagging, dedup candidates | Cheapest capable model |

Deterministic quantitative calculations call no model. Model choice, prompt
version, token usage, and cost are recorded per run.

---

## 7. Observability

Every agent run records: run ID, parent run ID, agent, model, prompt version,
input versions, output artifact ID, latency, token usage, cost, status,
errors, and retries. Agent runs are queryable alongside deterministic runs so
a conclusion's full provenance includes which model said what, when, and at
what cost.

---

## 8. Failure and degradation

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
