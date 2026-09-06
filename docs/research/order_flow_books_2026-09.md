# Book evidence map: order flow, microstructure, and NQ research

Status: **bibliographic reconnaissance; proposed research input, not a
strategy record.**

Date: 2026-09-06.

## 1. Purpose and boundaries

This note is a source map for the Research Agent's first reading queue.  It
does **not** claim that any book establishes a tradable NQ edge, chooses a
vendor, selects a data tier, or advances Phase 1.  It does not quote or
reproduce book content beyond bibliographic and publisher-supplied summaries.
The books have not been treated as substitutes for original empirical papers,
exchange rules, or a capability record for the actual NQ feed.

Claims below are intentionally separated into:

- **publisher/catalog fact** — title, author, edition, scope or contents from
  the linked publisher/catalog record;
- **methodological value** — a bounded use that OFA can make of the material;
- **practitioner heuristic** — terminology or a discretionary framing that
  may generate a hypothesis but supplies no empirical conclusion by itself;
- **research lead** — a proposed falsifiable question with minimum data and
  provenance requirements.  A lead must still pass
  `docs/research_protocol.md` §3 before it becomes an experiment.

The source class is "book".  Publisher prestige, author affiliation, and a
book's use in practice are not evidence that a setup works in CME NQ futures.
Instrument, venue, era, and market-design transfer are open empirical
questions.

## 2. Reading queue

### 2.1 Larry Harris — *Trading and Exchanges: Market Microstructure for Practitioners*

- **Bibliographic source:** [Oxford Academic record](https://academic.oup.com/book/52292),
  Larry Harris, Oxford University Press, published 2002; print ISBN
  9780195144703.  The publisher's contents include order-driven markets,
  order properties, price/time precedence, liquidity, bid/ask spreads and
  transaction-cost measurement.
- **Bounded scope:** a broad institutional and economic account of trading
  venues, orders, liquidity supply, and transaction costs.  It covers many
  market structures; it is not an NQ/CME implementation specification.
- **Methodological value:** use it to separate an order's mechanics,
  liquidity, spread/cost and participant incentives before attempting to name
  a feature.  It supports a requirement that a proposed "book-pressure" or
  "liquidity" measure state the actual market mechanism it intends to proxy.
- **Risks and unsupported claims:** its broad treatment does not verify CME
  matching, implied-order treatment, timestamp meaning, or a modern feed's
  sequence semantics.  A theoretical mechanism is not a directional forecast.
- **Research leads (proposals only):**
  1. Test whether a pre-defined top-of-book state transition adds information
     beyond spread, time-of-day and volatility controls. Minimum data:
     synchronized trades and BBO/MBP updates; quote/depth fields `OBSERVED`;
     the transition is `RECONSTRUCTED` only from an exact, gap-free ordered
     stream; and a decision-time mapping satisfying the `ts_recv` rule.
  2. Test whether a signal's gross effect remains after a pre-registered
     conservative spread, commission, latency and slippage stress.  Those
     costs and fills are `SIMULATED`; no historical order book makes them
     observed.

### 2.2 Joel Hasbrouck — *Empirical Market Microstructure*

- **Bibliographic source:** [Oxford Academic record](https://academic.oup.com/book/52241),
  Joel Hasbrouck, Oxford University Press, published 2007; print ISBN
  9780195301649.  Its listed contents span trading mechanisms, sequential
  trade models, order flow, limit-order markets, depth, and trading costs.
- **Bounded scope:** econometric frameworks for studying trades, quotes,
  information and price formation.  The catalog describes securities trading;
  direct applicability to CME futures must be tested rather than assumed.
- **Methodological value:** an evidence-oriented alternative to chart
  narratives: formulate measurable conditional relations and compare them to
  an explicit null rather than labelling price movement "absorption" after the
  fact.
- **Risks and unsupported claims:** model estimates can be misspecified,
  sensitive to sampling and affected by trade-sign classification.  A signed
  trade series inferred from prices is `INFERRED`, not observed order
  aggressor side.  A book-level framework does not settle causal direction or
  predictability after execution costs.
- **Research leads (proposals only):**
  1. Pre-register a conditional-response study of NQ mid-price movement after
     signed trade imbalance, then compare it with time-of-day- and
     volatility-matched nulls.  Minimum data: trades, contemporaneous BBO and
     observed aggressor side; if side is inferred, report unknown/inferred
     share and run it as a separate capability tier.
  2. Test a *location-only* condition against the same condition augmented by
     a pre-defined flow measure.  The ablation directly addresses the risk
     that a supposed order-flow signal is only a location effect.  Labels must
     be generated in the separate future labelling pass, with purge width
     driven by the declared label horizon.

### 2.3 Jean-Philippe Bouchaud, Julius Bonart, Jonathan Donier, and Martin Gould — *Trades, Quotes and Prices: Financial Markets Under the Microscope*

- **Bibliographic source:** [Cambridge University Press contents](https://www.cambridge.org/core/books/trades-quotes-and-prices/contents/2CF529EB88C0C8C02A50961FD7A92DEE)
  and [publisher listing](https://www.cambridge.org/core/books/trades-quotes-and-prices/029A71078EE4C41C0D5D4574211AB1B5/listing),
  Cambridge University Press, print publication 2018, DOI
  [10.1017/9781316659335](https://doi.org/10.1017/9781316659335).  Its stated
  structure covers limit-order books, correlations, price impact, adverse
  selection and liquidity provision.
- **Bounded scope:** a modern microstructure text joining models and empirical
  phenomena around trades, quotes and price impact.  It is useful for
  specifying what an order-book observation can and cannot identify.
- **Methodological value:** use it to challenge simplistic readings of depth:
  displayed liquidity is dynamic, and trade impact, adverse selection and
  resiliency must be measured as time-ordered relations rather than as a
  static chart pattern.
- **Risks and unsupported claims:** empirical regularities may vary with tick
  size, venue rules, sampling method and period.  MBP depth is not queue
  identity; MBO still does not observe our hypothetical queue position.
  "Pulling," "sweep," and intent classifications remain `INFERRED` unless
  their operational definition and error behaviour are established.
- **Research leads (proposals only):**
  1. Compare a bounded pre-event depth-change measure with a matched static
     depth measure for subsequent price response, after excluding stale or
     gapped book intervals.  Minimum data: MBP-10 or better with explicit
     snapshot/delta semantics, `OBSERVED` depth fields and verified ordering.
  2. Test whether a defined post-trade book-replenishment measure has
     incremental association beyond signed trade size and location.  Minimum
     data: MBO for queue/order-level claims; MBP may support only an aggregate
     depth-change version.  The latter must not be presented as replenishment
     by a particular participant.

### 2.4 Álvaro Cartea, Sebastian Jaimungal, and José Penalva — *Algorithmic and High-Frequency Trading*

- **Bibliographic source:** [Cambridge University Press front matter](https://assets.cambridge.org/97811070/91146/frontmatter/9781107091146_frontmatter.pdf)
  and [Cambridge catalog search result](https://www.cambridge.org/us/search?currentTheme=Academic_v1&page=1&query=algorithmic+finance&searchSubmitProducts=Academic&site=&tab=related),
  Cambridge University Press, 2015, ISBN 9781107091146.  The publisher
  describes models for execution, market making, VWAP schedules, pairs and
  dark-pool trading, grounded in exchange mechanics and adverse selection.
- **Bounded scope:** mathematical models of algorithmic trading and execution
  decisions.  It is not an entitlement statement, a retail-latency model, or
  a license to use a model's assumptions in CME NQ.
- **Methodological value:** supplies a disciplined reason to distinguish a
  predictive research question from an execution question.  It reinforces
  that latency, adverse selection, spread and inventory exposure belong in
  pre-specified stress analysis, not post-hoc excuses.
- **Risks and unsupported claims:** stylized models and institutional
  assumptions can be inappropriate for a smaller participant; market-making
  models may require information and latency unavailable to OFA.  No result
  can assume a fill or queue position from observed book data.  Those are
  `SIMULATED` and must be varied conservatively.
- **Research leads (proposals only):**
  1. For any future aggressive-entry hypothesis, vary explicit simulated
     arrival latency and slippage over a pre-registered range and reject the
     hypothesis if it fails the conservative range.  Minimum data: decision
     timestamps with an explicit receive-time treatment plus trades/BBO.
  2. For any future passive-order hypothesis, use multiple queue/fill models
     as sensitivity cases, not as an observed feature or a source of alpha.
     Minimum data: MBO for a queue-aware approximation; CME allocation rules
     and feed treatment must be independently verified first.

### 2.5 James F. Dalton, Robert B. Dalton, and Eric T. Jones — *Mind Over Markets: Power Trading with Market Generated Information*, updated edition

- **Bibliographic source:** [Wiley record](https://uat.store.wiley.com/en-us/mind-over-markets-power-trading-with-market-generated-information-updated-edition-p-9781118659724),
  Wiley, 2015, ISBN 9781118659724.  Wiley describes it as an updated guide to
  Market Profile; the accompanying [Wiley Online Library chapter record](https://onlinelibrary.wiley.com/doi/10.1002/9781118659724.ch2)
  identifies TPOs as its basic graphical building blocks.
- **Bounded scope:** practitioner treatment of Market Profile / auction-market
  language.  It is useful for locating vocabulary such as balance, value,
  initial balance and auction reference levels.
- **Practitioner heuristic, not empirical evidence:** terms such as
  "acceptance," "rejection," "exhaustion" or a profile shape are descriptions
  until OFA gives them a deterministic definition and validates them.  The
  publisher's marketing claims are not independent evidence of profitability.
- **Methodological value:** use it as a controlled vocabulary source for the
  `market_structure` Feature Specification profile, while requiring every
  visual/discretionary phrase to be converted into units, session policy,
  lookback, edge cases and a null comparison.
- **Risks and unsupported claims:** value-area conventions are not universal;
  session templates, TPO versus volume construction, roll handling and NQ
  session boundaries change results.  A completed-session statistic must
  never be visible inside that same session, and a prior-session level must
  reset at roll for price-level state.
- **Research leads (proposals only):**
  1. Define a prior-session reference level from trades using one explicitly
     chosen construction, then test it against a time-of-day-matched and
     location-only baseline.  Minimum data: trades `OBSERVED`; a verified
     session/calendar and trade-date policy; exact fixed-point prices.  The
     level is `RECONSTRUCTED`, not observed.
  2. Compare candidate value-area constructions as separate variants within
     one declared hypothesis family.  Record every construction and parameter
     tried in the discovery-search log; never report the best convention as a
     one-off discovery.

### 2.6 Marcos López de Prado — *Advances in Financial Machine Learning*

- **Bibliographic source:** [Wiley record](https://uat.store.wiley.com/en-us/advances-in-financial-machine-learning-p-9781119482109),
  Wiley, 2018, ISBN 9781119482109.  The publisher describes coverage of data
  structuring, ML research and backtesting while avoiding false positives.
- **Bounded scope:** research-method and validation material, not a source of
  order-flow mechanics or a justification for using machine learning.  OFA
  explicitly defers ML prediction and automated optimisation.
- **Methodological value:** a prompt to audit leakage, multiple testing,
  labels and backtest selection.  OFA's binding rules remain
  `docs/research_protocol.md` and `docs/validation_protocol.md`; no method is
  adopted merely because it appears in a book.
- **Risks and unsupported claims:** methods have assumptions and can be
  misapplied to irregular event streams, overlapping labels and nonstationary
  futures regimes.  Book examples do not demonstrate NQ profitability and do
  not override the project's chronological, purge, embargo and warm-up rules.
- **Research leads (proposals only):**
  1. For each eventual order-flow label, compare the pre-registered split
     policy with an adversarial leakage audit that checks overlapping outcome
     horizons at every boundary.  Minimum data: deterministic replay and a
     label horizon; this is blocked until the later label/split phases.
  2. Treat each definition and threshold variation as a member of a declared
     hypothesis family, with a self-reported discovery-search log and an
     adjusted acceptance threshold.  This is protocol design, not a trading
     signal.

## 3. Cross-book synthesis: what can and cannot enter OFA

| Theme | Evidence status | Permitted present use | Not permitted |
| --- | --- | --- | --- |
| Market mechanism, liquidity, price impact | Scholarly books frame mechanisms and measurable questions | Create bounded hypotheses and capability requirements | Claim a mechanism predicts NQ or infer hidden intent from a chart/book snapshot |
| Order-book dynamics | Books motivate time-ordered analysis; actual feed fields remain unverified for the selected scope | Identify whether MBP-10 or MBO would be minimally required | Treat MBP depth as queue identity or treat a vendor timestamp as decision availability |
| Market/Profile terminology | Practitioner vocabulary, not independent evidence of edge | Formalize competing definitions and use location-only ablations | Implement visual/discretionary labels or use developing completed-session values |
| Execution and latency | Models are useful for stress design | Specify conservative `SIMULATED` cost, latency and fill sensitivities | Present simulated fills, queue position or slippage as observed performance |
| Validation hygiene | Methodological source plus OFA's binding protocol | Pre-register labels, splits, purge, embargo, warm-up and multiplicity accounting | Tune on confirmation/holdout or introduce ML/optimisation early |

## 4. Reading and evidence workflow proposed for the Research Agent

1. Extract a claim only at the granularity that the source supports, recording
   page/chapter when licensed access is available.  A catalog/TOC supports
   scope, not a substantive empirical claim.
2. Classify each item as `ESTABLISHED`, `SUPPORTED`, `PLAUSIBLE`,
   `SPECULATIVE`, or `UNKNOWN` under `docs/research_protocol.md` §13.  This
   initial map intentionally assigns no positive-edge rating.
3. Search for original empirical papers that support and contradict each
   proposed mechanism; record market, venue, sample interval and data
   granularity.  Repeated commentary does not count as independent support.
4. Hand a proposed definition to the appropriate Feature Specification
   profile.  It must declare formulas, event/time basis, units, capability,
   provenance, gap/reset and roll behaviour before strategy use.
5. Have an independent Adversarial review attack transfer from the source's
   market to NQ, timestamp causality, trade-sign inference, execution
   realism, location-only explanations and multiple testing.
6. Only then create an `OF-XXXX` idea record; never advance it past `IDEA`
   without the complete hypothesis, label, baseline, split policy and
   thresholds required by `docs/research_protocol.md`.

## 5. Open limitations carried forward

- No selected vendor or capability record exists for the eventual NQ research
  data.  In particular, `ts_recv` capture point, sequence scope,
  snapshot/delta semantics, aggressor-side availability and MBO entitlement
  remain governed by `docs/limitations.md` and `docs/vendor_capability_matrix.md`.
- The project has no canonical-event contract, Feature/Lookback contract,
  deterministic event store, label engine, backtester or validation engine
  yet.  This note must not be read as authority to implement any of them.
- NQ-specific evidence requires futures/CME-specific primary material and
  empirical testing; equity or generic electronic-market results are
  hypotheses for transfer, not confirmation.
