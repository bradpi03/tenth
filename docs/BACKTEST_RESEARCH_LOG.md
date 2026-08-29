# TENTH — BACKTEST RESEARCH LOG

This document records the experimental history of TENTH as a research project and is intended to reduce hindsight bias, parameter chasing, and loss of methodological context as the project evolves.

The log is intentionally evidence-based and conservative. If a result or exact detail cannot be reliably recovered from the repository, git history, comments, or existing documentation, it is explicitly marked as "Not reliably recoverable from current repository history" rather than guessed.

---

## BACKTEST 001 — AAPL TREND BASELINE

### Purpose / hypothesis
To test the first simple trend-following idea on a liquid equity: when a short-term moving average remains above a longer-term moving average, does the strategy capture directional upside over a multi-year sample while respecting a previous-day signal rule to avoid look-ahead bias?

### Strategy
- Asset: AAPL
- Data: five years of daily data
- Signal: previous-day SMA20 > SMA50
- Position: in market when the previous-day signal is bullish
- Starting capital: $1,000
- Look-ahead protection: use previous-day signal rather than same-day signal

### Dataset
- Asset(s): AAPL
- Test period: Not reliably recoverable from current repository history, but the project history indicates a five-year daily dataset was used.
- Data frequency: daily
- Transaction costs: Not reliably recoverable from current repository history; the project later standardised to 0.10% entry / 0.10% exit, but the original Backtest 001 implementation is not fully recoverable from the current repo history alone.

### Change from previous test
This was the first strategy implementation, so there is no prior backtest to compare against. It established the basic AAPL trend-following prototype.

### Key results
- Not reliably recoverable from current repository history.

### Interpretation
This was the initial baseline experiment to confirm that a simple moving-average trend rule could be tested with realistic portfolio accounting and no same-day look-ahead.

### Decision
- retained (as conceptual baseline)

### Research integrity
- Look-ahead bias protection was explicitly part of the design.
- Exact performance metrics are not reliably recoverable from current repository history.

---

## BACKTEST 002 — EARLY VALIDATION / BASELINE EXTENSION

### Purpose / hypothesis
To continue the initial AAPL trend-following investigation by validating the simple baseline under a more structured comparison framework and preserving the original experimental rules while adding more explicit reporting.

### Strategy
- A continuation of the original AAPL baseline using the same trend idea.
- Use previous-day signal logic to avoid look-ahead bias.
- Keep the strategy rule simple and not parameter-tuned.

### Dataset
- Asset(s): AAPL
- Test period: the project history indicates the same five-year daily sample used for the original AAPL strategy.
- Data frequency: daily
- Transaction costs: Not reliably recoverable from current repository history.

### Change from previous test
Backtest 002 is part of the evolution from the original AAPL prototype into a structured validation script. The project history indicates it built on the original rule rather than changing the core trend definition.

### Key results
- Not reliably recoverable from current repository history.

### Interpretation
This was an intermediate structural benchmark rather than a materially different strategy hypothesis. It served to formalise the testing framework as the project moved toward multi-asset comparison.

### Decision
- retained as baseline framing

### Research integrity
- No evidence of optimisation or rule drift is evident in the project documentation available here.
- Exact metrics are not reliably recoverable from current repository history.

---

## BACKTEST 003 — ORIGINAL TREND FOLLOWER

### Purpose / hypothesis
To test a simple trend-following system using the original entry and exit logic that became the project baseline for later validation work.

### Strategy
- Entry: previous-day SMA20 > SMA50 and previous-day RSI(14) > 50
- Exit: previous-day trend fails or previous-day RSI(14) <= 50
- Long-only daily strategy
- Transaction cost: 0.10% entry / 0.10% exit
- Starting capital: $1,000
- Previous-day signal handling preserved to avoid look-ahead bias

### Dataset
- Asset(s): AAPL, MSFT, GOOGL, AMZN, NVDA, JPM, XOM, SPY in later cross-asset work
- Test period: five years of daily data in the project’s main validation script
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

### Change from previous test
Backtest 003 formalised the original entry/exit logic as a clean baseline and became the reference strategy for later variants.

### Key results
- Available from project history and validation output: the strategy was a positive-return system for the original 8-asset sample in many cases, but it did not outperform Buy & Hold on a total-return basis in the 5-year test window.
- Backtest 003 outcomes were later used as the direct comparison baseline for Backtests 005 and 006.
- Summary values from project history:
  - median annualised return: 4.50%
  - median Sharpe ratio: 0.31
  - median max drawdown: -24.21%
  - median market exposure: 39.1%

### Interpretation
Backtest 003 established the original trend-following benchmark. It was an active baseline, not the final answer. It offered a reasonable trend-following implementation but with mixed performance and no evidence of broad Buy & Hold alpha.

### Decision
- retained as benchmark / baseline

### Research integrity
- This was a clean baseline strategy and was not tuned in later phases.
- It served as the direct comparison standard for Backtests 005 and 006.

---

## BACKTEST 004 — CROSS-ASSET VALIDATION

### Purpose / hypothesis
To test whether the original trend-following logic behaved consistently across multiple liquid US equities rather than only on a single stock.

### Strategy
- Use the same Backtest 003 logic across a set of major listed equities and SPY.
- Preserve transaction costs and previous-day signal logic.

### Dataset
- Asset(s): AAPL, MSFT, GOOGL, AMZN, NVDA, JPM, XOM, SPY
- Test period: five years of daily data for the main validation script
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

### Change from previous test
Backtest 004 broadened the evaluation universe from a single asset to the broader initial set of assets. It was a check for generalisation, not a strategy redesign.

### Key results
- The git history shows this commit was named "Add cross-asset validation Backtest 004".
- Exact detailed metrics are not reliably recoverable from the current repository history.

### Interpretation
This was a validation experiment intended to see whether the original trend strategy generalised beyond AAPL. The evidence available in project history suggests the results were mixed and did not justify treating the strategy as broadly superior to Buy & Hold.

### Decision
- validation only

### Research integrity
- This was not an optimisation step.
- It broadened the test universe while preserving the baseline logic.

---

## BACKTEST 005 — TREND-PERSISTENCE EXIT TEST

### Purpose / hypothesis
To test whether removing RSI from the exit rule changes behaviour materially. The hypothesis was that exit discipline based only on trend failure may reduce whipsaw and improve risk-adjusted behaviour while preserving the original entry logic.

### Strategy
- Entry: same as Backtest 003
  - previous-day SMA20 > SMA50
  - previous-day RSI(14) > 50
- Exit: previous-day trend fails only; RSI is not an exit trigger
- Transaction cost: 0.10% entry / 0.10% exit
- Look-ahead protection: previous-day signals retained

### Dataset
- Asset(s): AAPL, MSFT, GOOGL, AMZN, NVDA, JPM, XOM, SPY
- Test period: five years of daily data
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

### Change from previous test
The exit rule changed while the entry logic and costs remained the same. The purpose was to isolate the effect of trend persistence as the sole exit trigger.

### Key results
From project history / validation output:
- Positive-return assets, 005: 6 / 8
- Assets where 005 beats 003: 6 / 8
- Assets where 005 Sharpe exceeds 003: 4 / 8
- Assets where 005 drawdown is smaller than 003: 8 / 8
- median annualised return, 003: 4.50%
- median annualised return, 005: 6.59%
- median Sharpe ratio, 003: 0.31
- median Sharpe ratio, 005: 0.35
- median max drawdown, 003: -24.21%
- median max drawdown, 005: -32.55%
- median market exposure, 003: 39.1%
- median market exposure, 005: 58.4%

### Interpretation
This experiment showed that the trend-only exit rule can improve some return and Sharpe outcomes while increasing market exposure and in some cases increasing drawdown. This was not treated as a final answer; it was a structural test of the exit logic.

### Decision
- retained as a validated variant, not a final strategy

### Research integrity
- This was a single-variable exit rule change intended to isolate one mechanism.
- No parameter optimisation was introduced.

---

## BACKTEST 006 — LONG-TERM TREND FILTER

### Purpose / hypothesis
To test whether adding a long-term trend filter reduces risk and drawdown without materially distorting the original strategy logic. The specific idea was to require the market to be above its 200-day average in addition to the existing short-term trend and RSI condition.

### Strategy
Entry rules:
- previous-day SMA20 > SMA50
- previous-day RSI(14) > 50
- previous-day Close > SMA200

Exit rule:
- original Backtest 003 exit logic
- exit when previous-day trend fails or RSI(14) <= 50

Additional structural details:
- previous-day signals used throughout
- same transaction costs as prior backtests
- same long-only structure

### Dataset
- Asset(s): AAPL, MSFT, GOOGL, AMZN, NVDA, JPM, XOM, SPY
- Test period: five years of daily data
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

### Change from previous test
Backtest 006 added the long-term trend filter to the original Backtest 003 rule set without changing the underlying exit logic. This was a frozen candidate strategy for later out-of-sample testing.

### Key results
Project history indicates:
- Positive-return assets, 006: 6 / 8
- Assets where 006 beats 003: 5 / 8
- Assets where 006 Sharpe exceeds 003: 5 / 8
- Assets where 006 drawdown is smaller than 003: 2 / 8
- median annualised return, 006: 7.38%
- median Sharpe ratio, 006: 0.60
- median max drawdown, 006: -22.22%
- median market exposure, 006: 34.2%

### Interpretation
Backtest 006 showed a more conservative profile than Backtest 003. The strategy reduced market exposure and often lowered drawdown, but it was still not a broad Buy & Hold outperformance strategy. This was treated as a candidate risk-management filter rather than as proven alpha.

### Decision
- retained as frozen candidate strategy

### Research integrity
- This was the first explicit long-term trend filter candidate.
- The strategy was preserved as a frozen rule set for Backtest 007.
- No optimisation was introduced after this point.

---

## BACKTEST 007 — OUT-OF-SAMPLE VALIDATION

### Purpose / hypothesis
To test the frozen Backtest 006 strategy on historical data that was not used during strategy development, without changing the rules.

### Strategy
Frozen Backtest 006 rules exactly:
- previous-day SMA20 > SMA50
- previous-day RSI(14) > 50
- previous-day Close > SMA200
- exit using the original Backtest 003 exit logic
- same look-ahead protections and transaction costs

### Dataset
- Asset(s): original 8 assets used in the project benchmark set
- Development window / validation window used for Backtest 006: 2021-08-28 to 2026-08-27
- Out-of-sample period used for Backtest 007: 2016-08-28 to 2021-08-27
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit
- Warm-up: permitted as needed for indicator calculations, but all reported performance calculations were constrained to the defined Backtest 007 test period

### Change from previous test
Backtest 007 froze the Backtest 006 strategy and tested it on the preceding non-overlapping five-year period instead of reusing the same recent sample. This was a true out-of-sample check for the frozen candidate.

### Key results
Verified final output from the run:
- Eligible assets: 8
- Positive-return strategy assets: 7 / 8
- Strategy beats Buy & Hold total return: 1 / 8
- Strategy Sharpe exceeds Buy & Hold: 2 / 8
- Strategy max drawdown is smaller than Buy & Hold: 1 / 8
- Median strategy annualised return: 9.03%
- Median Buy & Hold annualised return: 31.77%
- Median strategy Sharpe: 0.65
- Median Buy & Hold Sharpe: 1.13
- Median strategy max drawdown: -26.52%
- Median Buy & Hold max drawdown: -36.31%
- Median strategy market exposure: 48.5%

### Interpretation
The frozen strategy did not outperform Buy & Hold on the out-of-sample sample in aggregate. It materially reduced market exposure and reduced drawdown on some assets, but it did not show broad return leadership. The evidence remains consistent with a risk-management / drawdown filter role rather than proven alpha.

### Decision
- validation only

### Research integrity
- No strategy changes were made during the test.
- The out-of-sample window was explicitly separate from the development window.
- This was a non-overlapping validation step intended to reduce hindsight bias.

---

## BACKTEST 008 — ROBUSTNESS AUDIT

### Purpose / hypothesis
To audit the maximum drawdown comparison logic and broaden the out-of-sample robustness check to additional assets while keeping the frozen Backtest 006 strategy unchanged.

### Strategy
Same frozen strategy as Backtest 006:
- previous-day SMA20 > SMA50
- previous-day RSI(14) > 50
- previous-day Close > SMA200
- exit using original Backtest 003 exit logic
- same transaction costs
- same look-ahead protections

### Dataset
Part 1: original 8 Backtest 007 assets
- Out-of-sample period: 2016-08-28 to 2021-08-27
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

Part 2: broader cross-asset robustness set
- Additional assets tested: META, NFLX, TSLA, INTC, IBM, CSCO, ORCL, WMT, COST, KO, PG, JNJ, PFE, CVX, BAC, GS, CAT, BA, DIS, GE
- Out-of-sample period: 2016-08-28 to 2021-08-27
- Data frequency: daily
- Transaction costs: 0.10% entry / 0.10% exit

### Change from previous test
Backtest 008 did not change the strategy. It corrected the maximum-drawdown comparison logic and expanded the robustness test to additional assets over the same out-of-sample period.

### Key results
The original drawdown comparison logic had a sign error because drawdowns were negative values. In other words, the comparison was reversed. The incorrect combined result was 4 / 28. The corrected and verified result is 24 / 28.

Corrected combined findings from the verified run:
- eligible assets: 28
- positive strategy returns: 17 / 28
- strategy beat Buy & Hold total return: 3 / 28
- strategy Sharpe exceeded Buy & Hold: 5 / 28
- strategy had smaller maximum drawdown: 24 / 28
- median strategy annualised return: 3.70%
- median Buy & Hold annualised return: 18.27%
- median strategy Sharpe: 0.26
- median Buy & Hold Sharpe: 0.71
- median strategy maximum drawdown: -28.53%
- median Buy & Hold maximum drawdown: -41.27%
- median strategy market exposure: 41.1%

Additional 20-asset summary:
- eligible assets: 20
- positive-return strategy assets: 10 / 20
- strategy beats Buy & Hold: 2 / 20
- strategy Sharpe exceeds Buy & Hold: 3 / 20
- strategy max drawdown is smaller than Buy & Hold: 17 / 20
- median strategy annualised return: 0.08%
- median Buy & Hold annualised return: 15.91%
- median strategy Sharpe: -0.01
- median Buy & Hold Sharpe: 0.64
- median strategy max drawdown: -29.58%
- median Buy & Hold max drawdown: -42.46%
- median strategy market exposure: 38.7%

Original 8-asset summary after correction:
- exact count where strategy drawdown is smaller: 7 / 8
- median Buy & Hold drawdown: -36.31%
- median strategy drawdown: -26.52%

### Interpretation
The corrected audit supports the view that the frozen strategy behaves more like a market-risk / drawdown reduction filter than a Buy & Hold outperforming return engine. It generally lowers market exposure and often reduces drawdown, but it substantially reduces upside participation. The data still does not justify treating it as proven alpha.

### Decision
- validation only

### Research integrity
- The initial Backtest 008 drawdown comparison used reversed sign logic because drawdowns were negative values.
- The incorrect combined result was 4 / 28.
- The comparison logic was corrected and the verified result is 24 / 28.
- No strategy rules, indicators, parameters, dates, transaction costs, or return calculations were changed during the audit.

---

# CURRENT RESEARCH STATUS

Frozen candidate:
Backtest 006

Evidence level:
Promising risk-management behaviour, not proven alpha.

Next research priority:
Investigate whether the reduction in drawdown can be achieved while retaining more upside WITHOUT parameter fitting or retrospectively optimising the existing test periods.

The strongest evidence so far is:

The frozen strategy appears to act primarily as a market-risk / drawdown reduction filter rather than a Buy & Hold outperforming return strategy.

It substantially reduces market exposure and historically reduced maximum drawdown across most of the tested assets, but at the cost of substantial upside participation.

This remains a research hypothesis requiring further validation.
