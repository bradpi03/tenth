# tenth — Trading Strategy

## Purpose

This document defines the trading approach that tenth will research, test and refine.

The objective is not to assume that a strategy works.

The objective is to discover whether a strategy has a statistically meaningful and repeatable edge after realistic costs and risk are considered.

---

## Initial Market

tenth will initially focus on liquid US-listed equities.

Initial universe:

- Large and mid-cap stocks
- Highly liquid securities
- Sufficient historical price and volume data
- Avoid extremely illiquid securities
- Avoid leveraged products initially

The trading universe can expand later.

---

## Trading Style

The initial focus will be short-term swing trading rather than high-frequency or intraday trading.

Typical holding period:

1–10 trading days.

This provides enough trading opportunities to experiment with compounding while avoiding the infrastructure requirements of high-frequency trading.

---

## Initial Strategy Hypothesis

The first strategy tenth will investigate is:

### Momentum + Trend + Volume

The hypothesis:

Stocks demonstrating strong recent momentum, trading within an established upward trend and supported by increased trading volume may have an increased probability of continuing higher over the short term.

This is a hypothesis to test — not an assumption.

---

## Candidate Entry Signals

Potential signals include:

- Price above a long-term moving average
- Short-term moving average above longer-term moving average
- Strong recent price momentum
- Relative strength versus the wider market
- Increasing trading volume
- Breakout above recent resistance
- Volatility within acceptable limits

The initial implementation should deliberately use only a small number of signals.

Additional signals should only be introduced when testing demonstrates that they improve the strategy.

---

## Candidate Exit Rules

Potential exits include:

- Stop-loss
- Trailing stop
- Profit target
- Momentum deterioration
- Trend reversal
- Maximum holding period
- Strategy signal reversal

Different exit methods should be tested rather than assumed.

---

## Risk Management

Risk management is a core component of the strategy.

tenth should eventually support:

- Maximum risk per trade
- Maximum position size
- Maximum portfolio exposure
- Maximum number of simultaneous positions
- Maximum acceptable drawdown
- Daily and weekly loss limits
- Emergency trading halt

No individual trade should be capable of causing catastrophic portfolio loss.

---

## Position Sizing

Position size should ultimately be calculated from risk rather than simply allocating equal amounts of capital.

Conceptually:

Position Size =
Acceptable Capital at Risk / Trade Risk

Position-sizing models will be tested during development.

---

## Costs

Backtesting must account for realistic trading friction, including where applicable:

- Commission
- Bid/ask spread
- Slippage
- Currency conversion
- Taxes or transaction charges

A strategy that only works when trading is assumed to be free should not be considered viable.

---

## Benchmark

Strategy performance should be compared against an appropriate passive benchmark.

Initial benchmark:

S&P 500 total return where suitable data is available.

The comparison should consider both return and risk.

---

## Performance Measures

At minimum tenth should calculate:

- Total return
- Annualised return
- Win rate
- Average winning trade
- Average losing trade
- Profit factor
- Maximum drawdown
- Volatility
- Sharpe ratio
- Number of trades
- Average holding period

Later versions may introduce additional metrics.

---

## Validation

A strategy should not be judged solely by its performance on the historical data used to create it.

Testing should eventually include:

Historical Data
↓
Development Period
↓
Out-of-Sample Testing
↓
Walk-Forward Testing
↓
Paper Trading
↓
Live Trading

This is intended to reduce overfitting and false confidence.

---

## Initial Experiment

The first experiment should remain deliberately simple.

Example hypothesis:

> Among liquid US equities already in an established uptrend, does buying strong short-term momentum accompanied by elevated volume produce positive risk-adjusted returns over the following several trading days?

tenth will test the hypothesis against historical data.

The results — positive or negative — determine what happens next.

---

## Strategy Development Principle

tenth does not exist to prove that a trading idea works.

tenth exists to find out whether it works.
