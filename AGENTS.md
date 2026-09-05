# AGENTS.md

Read `CLAUDE.md` completely before proposing or changing code. It is the
operating contract. Use its Document Map to load every authoritative document
for the work at hand.

If documents conflict, resolve the conflict before implementation. Keep
implemented, tested, documented, deferred, and proposed claims distinct.

## Phase gates

Work on one gated phase at a time. A phase advances only when every documented
exit criterion passes, the phase as a whole satisfies the Definition of Done
in `CLAUDE.md`, and GitHub Actions is green where applicable.

The final `CanonicalEvent` representation and the `Feature` / `Lookback`
contracts are deliberately deferred. Open their named design gates before
implementing them. Vendor selection, runtime dependencies, credentials, paid
services, and live execution require explicit user approval.

## Locked system laws

- The deterministic path is `EVENT -> FEATURE -> SIGNAL -> RISK -> ORDER`.
  Models, agents, and network services remain outside it. Risk and execution
  are deterministic and authoritative.
- Backtest, replay, paper, and any future live mode share deterministic event
  semantics to the extent their declared capability tiers permit.
- Prices use integer fixed-point values. Tick conversion is exact; an off-grid
  price is an error. Float price arithmetic is forbidden in deterministic
  logic.
- Market-stream ordering is `(ts_event, sequence, ingest_index)`. The decision
  clock is `ts_recv`. A missing receive timestamp requires an explicit,
  recorded, reproducible, and stressable fallback.
- Preserve `OBSERVED`, `RECONSTRUCTED`, `INFERRED`, and `SIMULATED` provenance.
  Never present derived or counterfactual information as observed.
- Consumers declare required capabilities and fail closed when they are
  unavailable. Historical-to-live transfer requires compatible capability
  tiers.
- Prevent future and look-ahead leakage. Define warm-up and split-boundary
  behavior explicitly; label horizon determines purge width.
- Roll `RESET` is mandatory for price-level state.

## Engineering loop

For each milestone or bug:

1. Inspect the relevant implementation, tests, history, and current Git state.
2. Verify or reproduce the current behavior.
3. Plan the smallest coherent change and state its boundaries.
4. Implement with regression, property, or integration tests appropriate to
   the risk.
5. Run the local gates.
6. Review adversarially for architecture, correctness, temporal leakage,
   quantitative validity, failure modes, and reproducibility as applicable.
7. Fix material findings, rerun tests, and inspect the final diff for scope
   creep.
8. Commit a narrow change, push the current development branch, and verify the
   exact GitHub Actions run before declaring completion or advancing a phase.

Standard local gates:

```sh
make check
make guards
ofa version
git diff --check
git status --short --branch
```

Use `make check PYTHON=/path/to/python` when the development interpreter is not
named `python` or the environment is intentionally outside the checkout.

## Delegation and Git safety

Delegate only bounded investigation, implementation, or review that materially
improves speed or confidence. Use isolated worktrees for implementation where
supported, and never assign two implementation agents to the same subsystem.
Prefer reviewers who did not author the change. Avoid recursive spawning
without a concrete need.

The root agent reconciles findings, reviews every diff, runs final tests, and
alone decides on commits, pushes, and phase status. Report important subagent
findings and disagreements in the milestone summary. Subagents do not select
vendors, add dependencies, alter locked semantics, use credentials, weaken
tests, commit, or push.

Keep existing user changes intact. Avoid destructive Git operations. Never
force-push, rewrite pushed history, or run `git reset --hard` without explicit
user authorization. Never commit credentials, market data, generated run
artifacts, or unrelated cleanup.
