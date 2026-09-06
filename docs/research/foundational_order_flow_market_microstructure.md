# Foundational Order-Flow and Market-Microstructure Evidence

Status: **research evidence note — proposed input to later hypothesis work; no
strategy, feature, vendor, or data-source decision.**

Date: **2026-09-06**

## Scope and reading rule

This note is a small, primary-source-first reading set for the eventual NQ
research queue. It does **not** claim that an empirical result in equities or
ES transfers to NQ, and it does not claim an edge exists. NQ-specific evidence
must be produced on a declared NQ dataset before a hypothesis can be
formalized.

The sources fall into two groups:

- **Directly relevant CME E-mini evidence:** one source includes Nasdaq-100
  E-mini data, while several use ES. ES is still a different instrument from
  NQ, so it can establish a useful failure mode or data requirement, not an
  NQ result.
- **Cross-market limit-order-book evidence:** equity results are conceptual
  inputs only. Differences in venue rules, tick size, participant mix, period,
  and data construction are material threats to transfer.

Any candidate below must still satisfy the complete hypothesis specification,
pre-registered split policy, and thresholds in
[`docs/research_protocol.md`](../research_protocol.md). In particular, an
association with a *contemporaneous* price change is not a tradable prediction.

## Evidence summary

| Source | Setting | What it supports | What it does not support for OFA |
| --- | --- | --- | --- |
| Kurov and Lasser (2004) | Regular and E-mini S&P 500 and Nasdaq-100 futures | E-mini price discovery and trader identity mattered in its study period | A current NQ lead-lag edge or modern Globex participant classification |
| Biais, Hillion, and Spatt (1995) | Paris Bourse electronic limit order book | Book state and order submissions respond to liquidity conditions | An NQ threshold, a causal effect, or a strategy |
| Bouchaud et al. (2004) | Paris equity trades and quotes | Persistent trade-sign flow can be offset by liquidity response | A fixed impact law or a forecastable NQ return |
| Cont, Kukanov, and Stoikov (2014) | NYSE TAQ, 50 stocks | Best-quote order-flow imbalance is associated with short-horizon price changes | A causal/predictive NQ signal without out-of-sample testing |
| Budish, Cramton, and Shim (2015) | CME ES full order-book activity, 2005–2011 | Latency and message ordering are economically material | That a historical exchange timestamp is a tradable decision time |
| Kirilenko et al. (2017) | CME ES audit trail around 6 May 2010 | Stress-event liquidity/intermediation behavior differs from ordinary conditions | A general crash predictor or an execution model from trade prints alone |
| Easley, López de Prado, and O'Hara (2012) | High-frequency flow-toxicity methodology | A volume-synchronized toxicity construction is a testable research proposal | That VPIN predicts volatility or is valid under arbitrary trade classification |
| Andersen and Bondarenko (2014) | S&P 500 futures, VPIN re-examination | VPIN's apparent predictive content can be mechanical/classification-sensitive | Using VPIN without matched baselines and an adversarial replication |

## Source records

### 1. Kurov and Lasser — direct Nasdaq-100 E-mini evidence, with a dated market structure

**Citation / primary source.** Alexander Kurov and Dennis J. Lasser (2004),
“Price Dynamics in the Regular and E-Mini Futures Markets,” *Journal of
Financial and Quantitative Analysis* 39(2), 365–384,
[DOI: 10.1017/S0022109000003112](https://doi.org/10.1017/S0022109000003112);
[publisher record](https://www.cambridge.org/core/journals/journal-of-financial-and-quantitative-analysis/article/abs/price-dynamics-in-the-regular-and-emini-futures-markets/7DFA66D1DDCE701D5713CA6B92E18DF2).

**Study setting and data.** Transactions data for S&P 500 and Nasdaq-100
regular and E-mini futures, with attached trader-type identification codes;
the study includes the then-coexisting regular/open-outcry and E-mini markets.

**Supported claim.** The authors find that price discovery appeared to start
in the E-mini contracts and that trades initiated by exchange locals appeared
more informative than off-exchange customer trades. This is the most direct
source in this note for Nasdaq-100 E-mini futures and supports the modest
claim that NQ/E-mini is an appropriate venue for order-flow research.

**Limitations and contradictory considerations.** The institutional setting
predates the current all-electronic CME market and relies on trader-type and
floor-proximity information not normally present in historical market-data
feeds. It establishes neither a modern NQ lead-lag effect nor a current
participant-classification method.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** Do not translate the paper's local-versus-customer result into an
anonymous-feed signal. A narrower NQ study could ask whether a specified
market-data observable leads a separately labelled NQ response, while treating
participant identity as unavailable unless an entitled dataset demonstrably
contains it. It requires a capability record that distinguishes observed
participant fields from any inferred proxy.

### 2. Biais, Hillion, and Spatt — order placement reacts to book liquidity

**Citation / primary source.** Bruno Biais, Pierre Hillion, and Chester Spatt
(1995), “An Empirical Analysis of the Limit Order Book and the Order Flow in
the Paris Bourse,” *The Journal of Finance* 50(5), 1655–1689,
[DOI: 10.1111/j.1540-6261.1995.tb05192.x](https://doi.org/10.1111/j.1540-6261.1995.tb05192.x).

**Study setting and data.** A centralized computerized Paris equity limit
order market. The article studies the interaction of displayed book depth,
spread, trades, and order placement.

**Supported claim.** The authors document that thin books tend to elicit
orders, while thick books tend to result in trades; they also report quote
shifts after large purchases and sales. This supports treating liquidity
provision, cancellation, and aggressive trading as jointly evolving rather
than interpreting a displayed queue in isolation.

**Limitations and contradictory considerations.** This is a 1995 equity-market
study, not CME Globex or NQ. Its descriptive and association-based findings do
not identify a portable parameter or a causal trading rule. Book behavior can
change with matching rules, tick size, market-maker incentives, and message
technology. The later sources below also warn that trade-flow persistence and
liquidity responses can offset one another.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** Test whether a *pre-decision* NQ top-of-book thinness condition
changes the conditional response to subsequently observed aggressive flow,
relative to a time-of-day and volatility-matched baseline. This requires an
ordered observed BBO price-and-size stream plus observed book updates, with
explicit gap/reset handling. A feed that only supplies snapshots or conflated
updates may be insufficient to identify the relevant liquidity changes.

### 3. Bouchaud, Gefen, Potters, and Wyart — flow persistence can be offset

**Citation / primary source.** Jean-Philippe Bouchaud, Yuval Gefen, Marc
Potters, and Matthieu Wyart (2004), “Fluctuations and Response in Financial
Markets: The Subtle Nature of ‘Random’ Price Changes,” *Quantitative Finance*
4(2), 176–190, [DOI: 10.1088/1469-7688/4/2/007](https://doi.org/10.1088/1469-7688/4/2/007);
[author version](https://arxiv.org/abs/cond-mat/0307332).

**Study setting and data.** Trades and quotes from the Paris equity market;
the paper models price response to the history of signed trades.

**Supported claim.** The authors report long-range correlation in market-order
signs together with countervailing liquidity effects, offering an explanation
for prices that remain approximately diffusive. The supported lesson is not
that signed flow is useless, but that persistent signed flow alone need not
produce a persistent exploitable price drift.

**Limitations and contradictory considerations.** The result is based on a
different equity venue and a model with specific assumptions about the impact
propagator. Its interpretation is contested in the later literature; it is
not an estimate for CME futures. A fitted response curve is especially
vulnerable to hidden future information when aggregation windows are not
defined causally.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** Compare a past-only signed-flow statistic with the same statistic
conditioned on contemporaneous displayed depth. Pre-register whether the
incremental out-of-sample effect over depth-only and time-of-day baselines is
positive after costs. It requires trade direction at a declared provenance
tier and BBO/depth updates. If trade direction is derived from a tick rule, it
is `INFERRED`, not `OBSERVED`, and its error rate must be recorded and stressed.

### 4. Cont, Kukanov, and Stoikov — best-quote order-flow imbalance

**Citation / primary source.** Rama Cont, Arseniy Kukanov, and Sasha Stoikov
(2014), “The Price Impact of Order Book Events,” *Journal of Financial
Econometrics* 12(1), 47–88,
[DOI: 10.1093/jjfinec/nbt003](https://doi.org/10.1093/jjfinec/nbt003);
[author preprint](https://arxiv.org/abs/1011.6402).

**Study setting and data.** One calendar month of NYSE Trades and Quotes data
for 50 randomly selected S&P 500 stocks. The construction aggregates changes
at the best bid and ask from trades, limit orders, and cancellations.

**Supported claim.** Over short intervals in that sample, changes in the
mid-price were more strongly associated with their order-flow-imbalance (OFI)
measure than with traded volume; the fitted impact slope varied inversely with
depth. This supports evaluating *all* relevant best-quote events, rather than
using volume alone.

**Limitations and contradictory considerations.** The authors themselves note
that OFI includes price-changing book events, creating a possible tautology in
a contemporaneous regression. The finding is cross-sectional equity evidence,
not a causal NQ forecast. A completed interval OFI cannot be used to decide
inside that same interval; doing so would be look-ahead.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** At each NQ decision time, calculate OFI only from events already
available at that decision time, then test a *future* mid-price label against
depth-only, time-of-day, and random-entry baselines. Required capabilities are
observed best-bid/ask prices and sizes with a deterministic event order;
ideally observed add/cancel/trade semantics. If only aggregate book changes
are supplied, any event-type decomposition must be labelled
`RECONSTRUCTED` only when it is parameter-free and exact, otherwise
`INFERRED`.

### 5. Budish, Cramton, and Shim — latency is part of the economic setting

**Citation / primary source.** Eric Budish, Peter Cramton, and John Shim
(2015), “The High-Frequency Trading Arms Race: Frequent Batch Auctions as a
Market Design Response,” *The Quarterly Journal of Economics* 130(4),
1547–1621, [DOI: 10.1093/qje/qjv027](https://doi.org/10.1093/qje/qjv027);
[author-hosted record and PDF](https://www.econ.umd.edu/publication/high-frequency-trading-arms-race-frequent-batch-auctions-market-design-response-0).

**Study setting and data.** The empirical material includes all CME E-mini S&P
500 (ES) limit-order-book activity from 2005 through 2011, alongside related
cross-market analysis.

**Supported claim.** The paper documents economically meaningful races over
very short horizons in a continuous limit-order-book environment. For OFA,
the narrow supported implication is that timestamp resolution, ordering, and
the point at which data become usable are not bookkeeping details.

**Limitations and contradictory considerations.** This is ES rather than NQ,
and it is principally a market-design paper rather than an NQ predictive
strategy study. Historical replay cannot reproduce a participant’s actual
latency advantage merely by sorting events at the exchange timestamp.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** Every latency-sensitive NQ hypothesis should be tested under a
recorded decision clock and a stress range for downstream feed and order
     latency. It needs an explicit capture-point definition for `ts_recv`, source
     sequence semantics, and an auditable fallback when receive time is absent.
     `ts_event` is the first component of the full
     `(ts_event, sequence, ingest_index)` ordering key; it cannot be silently
     promoted into the decision clock.

### 6. Kirilenko, Kyle, Samadi, and Tuzun — stress events are not normal
liquidity

**Citation / primary source.** Andrei Kirilenko, Albert S. Kyle, Mehrdad
Samadi, and Tugkan Tuzun (2017), “The Flash Crash: High-Frequency Trading in
an Electronic Market,” *The Journal of Finance* 72(3), 967–998,
[DOI: 10.1111/jofi.12498](https://doi.org/10.1111/jofi.12498).

**Study setting and data.** CFTC audit-trail transaction-level data for CME ES
on 6 May 2010 and the preceding three days, during the Flash Crash and its
immediate comparison period.

**Supported claim.** In this event study, a large automated ES sell program
created exceptional selling pressure; the authors find that the trading
pattern of the most active non-designated intraday intermediaries did not
change when prices fell. This supports modelling stress liquidity and
intermediation as a distinct risk regime, not assuming normal-period fills
remain representative.

**Limitations and contradictory considerations.** It is an extreme-event,
four-day ES sample and includes account/audit-trail information that ordinary
market-data feeds do not expose. It does not identify a crash predictor, an NQ
signal, or a fill model. Its account labels and participant classification
cannot be reconstructed from anonymous prints or displayed depth.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** Treat an extreme imbalance/liquidity-depletion condition first as a
risk and execution-stress scenario, not as an entry signal. A later
experiment could test whether a pre-defined observable NQ stress state
predicts worse simulated fill outcomes. It needs observed book evolution plus
explicitly `SIMULATED` fills; account-level causal interpretations are out of
scope unless an entitled source actually supplies those fields.

### 7. Easley, López de Prado, and O'Hara — VPIN as a contested proposal

**Citation / primary source.** David Easley, Marcos López de Prado, and
Maureen O'Hara (2012), “Flow Toxicity and Liquidity in a High-Frequency
World,” *Review of Financial Studies* 25(5), 1457–1493,
[DOI: 10.1093/rfs/hhs053](https://doi.org/10.1093/rfs/hhs053);
[author SSRN record](https://ssrn.com/abstract=1695596).

**Study setting and data.** The paper introduces volume-synchronized
probability of informed trading (VPIN), which uses volume imbalance, trade
intensity, and a buy/sell trade-classification procedure to form a high
frequency “flow toxicity” measure.

**Supported claim.** The source establishes the authors’ proposed
construction and their reported empirical relation to short-horizon
toxicity-induced volatility. It also makes the data dependency explicit:
VPIN requires buy/sell classified trades.

**Limitations and contradictory considerations.** The claimed predictive
content is directly disputed by the peer-reviewed Andersen and Bondarenko
study below. The measure is materially sensitive to classification and volume
bucket design, creating a substantial multiple-testing and implementation
risk. It must not be treated as an observed quantity merely because its input
trades are observed.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** A later NQ test could compare a pre-registered VPIN construction
against current volume, current volatility, time-of-day, and simpler
signed-flow baselines for a *future* volatility label. It requires an explicit
trade-side provenance declaration and a separate labelling pass. This should
not be formalized until the adversarial replication in the next source can be
implemented.

### 8. Andersen and Bondarenko — VPIN needs adversarial benchmarks

**Citation / primary source.** Torben G. Andersen and Oleg Bondarenko (2014),
“VPIN and the Flash Crash,” *Journal of Financial Markets* 17(1), 1–46,
[DOI: 10.1016/j.finmar.2013.05.005](https://doi.org/10.1016/j.finmar.2013.05.005);
[author-hosted record](https://pure.au.dk/portal/en/publications/vpin-and-the-flash-crash/).

**Study setting and data.** A re-examination of VPIN using S&P 500 futures
tick data and alternative trade-classification choices.

**Supported claim.** The authors find VPIN to be a poor short-run-volatility
predictor after controlling for current trading intensity and volatility, and
attribute apparent predictive content largely to mechanical dependence. They
also find the result sensitive to trade classification.

**Limitations and contradictory considerations.** This is still S&P 500
futures rather than NQ, and the original authors published a rejoinder. The
disagreement does not prove VPIN can never work; it proves that an unbenchmarked
positive result is inadequate evidence.

**Potential falsifiable hypothesis and data needed — proposal, not an OFA
feature.** If a toxicity metric ever enters the NQ discovery queue, require a
paired adversarial test: match its update timing and inputs, control for
contemporaneous volume/volatility, vary the signed-trade classifier, and
compare against simpler baselines on an untouched confirmation segment. This
requires retained raw trade identity/order, a declared classifier version,
and full lineage of bucket and threshold choices.

## Cross-source implications for later research design

These are **research-process proposals**, not implemented controls or
architecture changes:

1. **Separate contemporaneous explanation from prediction.** OFI and related
   measures may explain a price move in a completed interval. A predictive
   test must emit its feature at a known decision time, then label only a
   future horizon. The label must remain unavailable to the feature.
2. **Treat trade direction honestly.** Exchange-provided aggressor side is
   `OBSERVED`; a tick-rule or quote-rule classification is `INFERRED` and
   requires error and sensitivity analysis. Do not label an inferred side as
   observed simply because the trade itself was observed.
3. **Use arrival availability, not exchange action time.** The literature on
   speed makes the existing OFA decision-clock rule material: decisions are
   timestamped at `ts_recv`; unavailable receive time requires a recorded,
   reproducible, stress-tested fallback.
4. **Do not silently collapse book events.** Whether a feed distinguishes
   add, cancel, modify, trade, recovery, and snapshot events is a capability
   question. A strategy needing that distinction must fail closed if the
   declared capability is absent.
5. **Pre-register the metric family.** Window lengths, depth levels, bucket
   sizes, normalization, regime filters, and thresholds are variants in the
   same hypothesis family unless a written protocol rationale says otherwise.
   Purge is driven by the chosen future label horizon and every split needs
   independent warm-up.
6. **Make extreme-event execution explicitly simulated.** A book-based fill,
   queue position, market impact, and latency outcome is `SIMULATED`; it is
   never evidence that an order would have filled. Stress scenarios should
   attack a result, not rescue it.

## Deliberate non-conclusions

- No source in this note selects Databento, Rithmic, CME DataMine, or any
  other provider.
- No source proves NQ OFI, depth imbalance, VPIN, “absorption,” or any other
  order-flow concept has an edge.
- No source supplies OFA’s deferred `CanonicalEvent`, `Feature`, or `Lookback`
  contracts.
- No source substitutes for per-partition capability records, an explicit
  receive-time capture-point decision, or actual NQ out-of-sample validation.
