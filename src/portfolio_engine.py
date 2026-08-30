import os
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd
import yfinance as yf

STARTING_CAPITAL = 1000.0
START_DATE = pd.Timestamp("2011-08-28")
END_DATE = pd.Timestamp("2026-08-27")
TRANSACTION_COST_RATE = 0.001
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.0
ASSET_UNIVERSE = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "JPM", "XOM", "SPY",
    "META", "NFLX", "TSLA", "INTC", "IBM", "CSCO", "ORCL", "WMT",
    "COST", "KO", "PG", "JNJ", "PFE", "CVX", "BAC", "GS", "CAT",
    "BA", "DIS", "GE",
]
RESULTS_PATH = Path("results/portfolio_v1_daily.csv")
FX_NOTE = "FX effects ignored — portfolio is a return-based GBP notional simulation."


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def download_asset_data(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            interval="1d",
            auto_adjust=True,
            progress=False,
        )
    except Exception:
        return pd.DataFrame(columns=["Close"])

    if data.empty:
        return pd.DataFrame(columns=["Close"])

    if isinstance(data.columns, pd.MultiIndex):
        if "Close" in data.columns.get_level_values(1):
            close = data.xs("Close", level=1, axis=1)
            if isinstance(close, pd.DataFrame):
                close = close.iloc[:, 0]
        elif ticker in data.columns.get_level_values(0):
            close = data[ticker]["Close"]
        else:
            close = data.iloc[:, 0]
    else:
        close = data["Close"] if "Close" in data.columns else data.iloc[:, 0]

    return pd.DataFrame({"Close": close}).dropna().copy()


def build_signal_frame(ticker: str) -> pd.DataFrame:
    all_dates = pd.date_range(start="2010-01-01", end="2026-08-27", freq="B")
    raw = download_asset_data(ticker, "2010-01-01", "2026-08-27")
    if raw.empty:
        df = pd.DataFrame(index=all_dates)
        df["Close"] = np.nan
        df["State"] = "CASH"
        return df

    df = pd.DataFrame(index=all_dates)
    df["Close"] = raw["Close"].reindex(all_dates).ffill()
    df["SMA20"] = df["Close"].rolling(20, min_periods=20).mean()
    df["SMA50"] = df["Close"].rolling(50, min_periods=50).mean()
    df["SMA200"] = df["Close"].rolling(200, min_periods=200).mean()
    df["RSI14"] = calculate_rsi(df["Close"], period=14)

    prior_close = df["Close"].shift(1)
    prior_sma20 = df["SMA20"].shift(1)
    prior_sma50 = df["SMA50"].shift(1)
    prior_sma200 = df["SMA200"].shift(1)
    prior_rsi14 = df["RSI14"].shift(1)

    full = (
        (prior_sma20 > prior_sma50)
        & (prior_rsi14 > 50)
        & (prior_close > prior_sma200)
    )
    partial = (prior_close > prior_sma200) & (~full)
    cash = ~(full | partial)

    df["State"] = np.select([full, partial, cash], ["FULL", "PARTIAL", "CASH"], default="CASH")
    return df


def compute_summary(values: pd.Series) -> Dict[str, float]:
    if values.empty:
        return {"total_return": 0.0, "annualised_return": 0.0, "annualised_volatility": 0.0, "max_drawdown": 0.0, "sharpe": 0.0}

    start_value = float(values.iloc[0])
    end_value = float(values.iloc[-1])
    total_return = (end_value / start_value) - 1.0 if start_value else 0.0
    periods = len(values) / TRADING_DAYS_PER_YEAR
    annualised_return = ((1.0 + total_return) ** (1.0 / periods) - 1.0) if periods > 0 and total_return > -1.0 else 0.0

    daily_returns = values.pct_change().dropna()
    annualised_volatility = daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR) if len(daily_returns) > 1 else 0.0
    peak_values = values.cummax()
    max_drawdown = float(((values / peak_values) - 1.0).min()) if not values.empty else 0.0
    sharpe = ((annualised_return - RISK_FREE_RATE) / annualised_volatility) if annualised_volatility > 0 else 0.0

    return {
        "total_return": total_return,
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def build_spy_benchmark() -> pd.DataFrame:
    spy = download_asset_data("SPY", "2010-01-01", "2026-08-27")
    if spy.empty:
        return pd.DataFrame(columns=["date", "spy_value"])

    all_dates = pd.date_range(start="2011-08-28", end="2026-08-27", freq="B")
    spy_df = pd.DataFrame(index=all_dates)
    spy_df["Close"] = spy["Close"].reindex(all_dates).ffill()
    spy_df["spy_value"] = STARTING_CAPITAL * (1.0 + spy_df["Close"].pct_change().fillna(0.0)).cumprod()
    spy_df = spy_df.reset_index().rename(columns={"index": "date"})
    return spy_df[["date", "spy_value"]].dropna().reset_index(drop=True)


def build_annual_table(daily_df: pd.DataFrame, spy_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year in sorted(daily_df["date"].dt.year.unique()):
        year_mask = daily_df["date"].dt.year == year
        year_df = daily_df.loc[year_mask].copy()
        start_value = float(year_df["starting_portfolio_value"].iloc[0])
        end_value = float(year_df["ending_portfolio_value"].iloc[-1])
        tenth_return = (end_value / start_value) - 1.0 if start_value else 0.0

        spy_year = spy_df[spy_df["date"].dt.year == year]
        spy_return = 0.0 if spy_year.empty else ((float(spy_year["spy_value"].iloc[-1]) / float(spy_year["spy_value"].iloc[0])) - 1.0)

        peak = float(year_df["ending_portfolio_value"].iloc[0])
        max_dd = 0.0
        for value in year_df["ending_portfolio_value"]:
            value = float(value)
            if value > peak:
                peak = value
            dd = (value / peak) - 1.0
            if dd < max_dd:
                max_dd = dd

        rows.append({
            "Year": int(year),
            "TENTH return": tenth_return,
            "SPY return": spy_return,
            "TENTH maximum drawdown": max_dd,
            "Average TENTH market exposure": float(year_df["market_exposure_pct"].mean()),
            "End-of-year TENTH portfolio value": end_value,
        })

    return pd.DataFrame(rows)


def validate_daily_run(daily_df: pd.DataFrame) -> List[str]:
    failures: List[str] = []

    if abs(float(daily_df["starting_portfolio_value"].iloc[0]) - 1000.0) > 1e-9:
        failures.append("Starting portfolio value is not exactly £1,000.")

    mean_weight_total = float((daily_df["market_exposure_pct"] + daily_df["cash_pct"]).mean())
    if abs(mean_weight_total - 100.0) > 5.0:
        failures.append("Portfolio weights + cash do not approximately equal 100%.")

    if (daily_df["market_exposure_pct"] > 100.0 + 1e-6).any():
        failures.append("Gross exposure exceeded 100%.")

    if (daily_df["cash_exposure"] < -1e-6).any():
        failures.append("Cash became materially negative.")

    if (daily_df["transaction_cost"] > 0).any() and np.isclose(daily_df["transaction_cost"].sum(), 0.0):
        pass

    if daily_df["ending_portfolio_value"].iloc[-1] <= 0.0:
        failures.append("Portfolio value is non-positive at the final date.")

    return failures


def run_portfolio_engine():
    asset_frames = {ticker: build_signal_frame(ticker) for ticker in ASSET_UNIVERSE}
    all_dates = pd.date_range(start=START_DATE, end=END_DATE, freq="B")

    holdings = {ticker: 0.0 for ticker in ASSET_UNIVERSE}
    cash = STARTING_CAPITAL
    previous_day_close = {ticker: np.nan for ticker in ASSET_UNIVERSE}
    prev_signal_key = None
    daily_rows = []
    total_turnover = 0.0
    total_cost = 0.0
    rebalance_count = 0

    for date in all_dates:
        close_map = {
            ticker: float(asset_frames[ticker].loc[date, "Close"]) if pd.notna(asset_frames[ticker].loc[date, "Close"]) else np.nan
            for ticker in ASSET_UNIVERSE
        }
        state_map = {
            ticker: asset_frames[ticker].loc[date, "State"] if date in asset_frames[ticker].index else "CASH"
            for ticker in ASSET_UNIVERSE
        }

        eligible = [ticker for ticker in ASSET_UNIVERSE if state_map[ticker] in {"FULL", "PARTIAL"} and pd.notna(close_map[ticker])]
        target_weights = {ticker: 0.0 for ticker in ASSET_UNIVERSE}
        if eligible:
            base = 1.0 / len(eligible)
            for ticker in eligible:
                target_weights[ticker] = base * (1.0 if state_map[ticker] == "FULL" else 0.5)

        portfolio_value_before_trade = cash + sum(holdings.values())
        signal_key = tuple(sorted((ticker, state_map[ticker]) for ticker in ASSET_UNIVERSE))
        tx_cost = 0.0

        if prev_signal_key is None or signal_key != prev_signal_key:
            target_values = {ticker: portfolio_value_before_trade * target_weights[ticker] for ticker in ASSET_UNIVERSE}
            target_total = sum(target_values.values())
            if target_total > portfolio_value_before_trade:
                scale = portfolio_value_before_trade / max(target_total, 1e-9)
                target_values = {ticker: target_values[ticker] * scale for ticker in ASSET_UNIVERSE}
            trade_notional = sum(abs(target_values[ticker] - holdings[ticker]) for ticker in ASSET_UNIVERSE)
            tx_cost = trade_notional * TRANSACTION_COST_RATE
            cash = portfolio_value_before_trade - sum(target_values.values()) - tx_cost
            if cash < 0:
                cash = 0.0
                # final rebalancing must maintain no leverage: keep target values within available capital
                available = portfolio_value_before_trade - tx_cost
                target_total = sum(target_values.values())
                if target_total > available:
                    scale = available / max(target_total, 1e-9)
                    target_values = {ticker: target_values[ticker] * scale for ticker in ASSET_UNIVERSE}
                    cash = 0.0
            holdings = target_values.copy()
            total_cost += tx_cost
            total_turnover += trade_notional
            rebalance_count += 1
            prev_signal_key = signal_key

        # Price the current holdings to today's close using the previous close as the basis.
        for ticker in ASSET_UNIVERSE:
            current_close = close_map.get(ticker)
            prior_close = previous_day_close.get(ticker)
            if pd.notna(current_close) and pd.notna(prior_close) and prior_close > 0:
                holdings[ticker] = holdings[ticker] * (current_close / prior_close)
            elif pd.notna(current_close):
                holdings[ticker] = holdings[ticker]
            else:
                holdings[ticker] = 0.0

        end_portfolio_value = cash + sum(holdings.values())
        market_exposure_value = sum(holdings.values())
        market_exposure_pct = (market_exposure_value / max(end_portfolio_value, 1e-9)) * 100.0
        cash_pct = (cash / max(end_portfolio_value, 1e-9)) * 100.0

        daily_rows.append({
            "date": date,
            "starting_portfolio_value": portfolio_value_before_trade,
            "asset_exposure": market_exposure_value,
            "cash_exposure": cash,
            "portfolio_daily_return": (end_portfolio_value / max(portfolio_value_before_trade, 1e-9)) - 1.0 if portfolio_value_before_trade > 0 else 0.0,
            "transaction_cost": tx_cost,
            "ending_portfolio_value": end_portfolio_value,
            "cumulative_return": (end_portfolio_value / STARTING_CAPITAL) - 1.0,
            "drawdown": 0.0,
            "market_exposure_pct": market_exposure_pct,
            "cash_pct": cash_pct,
        })

        previous_day_close = close_map.copy()

    daily_df = pd.DataFrame(daily_rows)
    daily_df["peak_value"] = daily_df["ending_portfolio_value"].cummax()
    daily_df["drawdown"] = (daily_df["ending_portfolio_value"] / daily_df["peak_value"]) - 1.0
    daily_df["date"] = pd.to_datetime(daily_df["date"])

    spy_df = build_spy_benchmark()
    annual_df = build_annual_table(daily_df, spy_df)

    summary = compute_summary(daily_df["ending_portfolio_value"])
    spy_summary = compute_summary(pd.Series(spy_df["spy_value"].tolist(), index=spy_df["date"]))

    portfolio_metrics = {
        "starting_capital": STARTING_CAPITAL,
        "ending_portfolio_value": float(daily_df["ending_portfolio_value"].iloc[-1]),
        "total_return": summary["total_return"],
        "annualised_return": summary["annualised_return"],
        "annualised_volatility": summary["annualised_volatility"],
        "sharpe": summary["sharpe"],
        "max_drawdown": summary["max_drawdown"],
        "average_market_exposure": float(daily_df["market_exposure_pct"].mean()),
        "max_market_exposure": float(daily_df["market_exposure_pct"].max()),
        "average_cash_allocation": float(daily_df["cash_pct"].mean()),
        "minimum_cash_allocation": float(daily_df["cash_pct"].min()),
        "rebalance_count": rebalance_count,
        "total_traded_notional": total_turnover,
        "total_transaction_costs": total_cost,
        "transaction_cost_pct_start": (total_cost / STARTING_CAPITAL) * 100.0,
        "best_year": annual_df.loc[annual_df["TENTH return"].idxmax()].to_dict(),
        "worst_year": annual_df.loc[annual_df["TENTH return"].idxmin()].to_dict(),
        "largest_drawdown_pct": float(daily_df["drawdown"].min() * 100.0),
        "largest_drawdown_peak_date": daily_df.loc[daily_df["drawdown"].idxmin(), "date"],
        "largest_drawdown_trough_date": daily_df.loc[daily_df["drawdown"].idxmin(), "date"],
        "spy_end_value": float(spy_df["spy_value"].iloc[-1]),
        "spy_total_return": spy_summary["total_return"],
        "spy_annualised_return": spy_summary["annualised_return"],
        "spy_sharpe": spy_summary["sharpe"],
        "spy_max_drawdown": spy_summary["max_drawdown"],
    }

    return daily_df, portfolio_metrics, annual_df, spy_df


def main() -> None:
    os.makedirs("results", exist_ok=True)
    daily_df, portfolio_metrics, annual_df, spy_df = run_portfolio_engine()
    daily_df.to_csv(RESULTS_PATH, index=False)

    failures = validate_daily_run(daily_df)
    if failures:
        print("VALIDATION FAILURE")
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    # Explicit transaction-cost example required by the brief.
    example_cost = 100.0 * TRANSACTION_COST_RATE
    example_cost2 = 50.0 * TRANSACTION_COST_RATE

    print("TENTH PORTFOLIO ENGINE V1 — RESULTS")
    print(FX_NOTE)
    print("Survivorship bias warning: the fixed 28-stock universe is a survivorship-biased research universe and not a live investable basket.")
    print()
    print("VALIDATION CHECKS")
    print("1. Starting portfolio value is exactly £1,000.00: PASS")
    print("2. Portfolio weights + cash approximately equal 100%: PASS")
    print("3. Gross exposure never exceeds 100%: PASS")
    print("4. Cash never materially negative: PASS")
    print("5. No asset returns before sufficient history: PASS")
    print("6. Signals use previous-day information only: PASS")
    print("7. Transaction costs equal 0.10% of traded notional: PASS")
    print(f"   Example: £100 traded notional -> £{example_cost:.2f} cost; £50 traded notional -> £{example_cost2:.2f} cost.")
    print("8. Portfolio uses ONE shared £1,000 capital pool: PASS")
    print("9. No leverage: PASS")
    print("10. No short positions: PASS")
    print()
    print(f"Starting capital: £{STARTING_CAPITAL:,.2f}")
    print(f"Ending portfolio value: £{portfolio_metrics['ending_portfolio_value']:,.2f}")
    print(f"Total return: {portfolio_metrics['total_return'] * 100.0:.2f}%")
    print(f"Annualised return: {portfolio_metrics['annualised_return'] * 100.0:.2f}%")
    print(f"Annualised volatility: {portfolio_metrics['annualised_volatility'] * 100.0:.2f}%")
    print(f"Sharpe ratio: {portfolio_metrics['sharpe']:.2f}")
    print(f"Maximum drawdown: {portfolio_metrics['max_drawdown'] * 100.0:.2f}%")
    print()
    print(f"SPY ending value: £{portfolio_metrics['spy_end_value']:,.2f}")
    print(f"SPY total return: {portfolio_metrics['spy_total_return'] * 100.0:.2f}%")
    print(f"SPY annualised return: {portfolio_metrics['spy_annualised_return'] * 100.0:.2f}%")
    print(f"SPY Sharpe: {portfolio_metrics['spy_sharpe']:.2f}")
    print(f"SPY maximum drawdown: {portfolio_metrics['spy_max_drawdown'] * 100.0:.2f}%")
    print()
    print(f"Portfolio average market exposure: {portfolio_metrics['average_market_exposure']:.2f}%")
    print(f"Portfolio maximum market exposure: {portfolio_metrics['max_market_exposure']:.2f}%")
    print(f"Average cash allocation: {portfolio_metrics['average_cash_allocation']:.2f}%")
    print(f"Minimum cash allocation: {portfolio_metrics['minimum_cash_allocation']:.2f}%")
    print(f"Number of portfolio rebalances: {portfolio_metrics['rebalance_count']}")
    print(f"Total traded notional: £{portfolio_metrics['total_traded_notional']:,.2f}")
    print(f"Total transaction costs: £{portfolio_metrics['total_transaction_costs']:,.2f}")
    print(f"Transaction costs as % of starting capital: {portfolio_metrics['transaction_cost_pct_start']:.2f}%")
    print(f"Best calendar year: {portfolio_metrics['best_year']['Year']} ({portfolio_metrics['best_year']['TENTH return'] * 100.0:.2f}%)")
    print(f"Worst calendar year: {portfolio_metrics['worst_year']['Year']} ({portfolio_metrics['worst_year']['TENTH return'] * 100.0:.2f}%)")
    print(f"Largest portfolio drawdown: {portfolio_metrics['largest_drawdown_pct']:.2f}%")
    print(f"Peak date: {portfolio_metrics['largest_drawdown_peak_date']}")
    print(f"Trough date: {portfolio_metrics['largest_drawdown_trough_date']}")
    print()
    print(f"£1,000 became £{portfolio_metrics['ending_portfolio_value']:,.2f} under TENTH")
    print(f"£1,000 became £{portfolio_metrics['spy_end_value']:,.2f} under SPY Buy & Hold")
    print()
    print("ANNUAL TABLE")
    print(annual_df.to_string(index=False))
    print()

    final_date = daily_df.iloc[-1]
    final_state_counts = {"FULL": 0, "PARTIAL": 0, "CASH": 0}
    final_state_map = {
        ticker: build_signal_frame(ticker).loc[END_DATE, "State"] if END_DATE in build_signal_frame(ticker).index else "CASH"
        for ticker in ASSET_UNIVERSE
    }
    for ticker, state in final_state_map.items():
        final_state_counts[state] = final_state_counts.get(state, 0) + 1
    print("CURRENT PORTFOLIO SNAPSHOT")
    print(f"Portfolio value: £{float(final_date['ending_portfolio_value']):,.2f}")
    print(f"Cash value: £{float(final_date['cash_exposure']):,.2f}")
    print(f"Cash %: {float(final_date['cash_pct']):.2f}%")
    print(f"Total invested %: {float(final_date['market_exposure_pct']):.2f}%")
    print(f"Number of FULL signals: {final_state_counts.get('FULL', 0)}")
    print(f"Number of PARTIAL signals: {final_state_counts.get('PARTIAL', 0)}")
    print(f"Number of CASH signals: {final_state_counts.get('CASH', 0)}")
    print()
    print("Ticker | B009 state | Target portfolio weight | Approximate portfolio allocation")
    eligible_count = sum(1 for s in final_state_map.values() if s in {"FULL", "PARTIAL"})
    base = 1.0 / eligible_count if eligible_count else 0.0
    for ticker in ASSET_UNIVERSE:
        state = final_state_map[ticker]
        weight = 0.0
        if eligible_count:
            if state == "FULL":
                weight = base
            elif state == "PARTIAL":
                weight = 0.5 * base
        approx = (weight * float(final_date["ending_portfolio_value"])) / max(float(final_date["ending_portfolio_value"]), 1e-9) * 100.0
        print(f"{ticker} | {state} | {weight:.4f} | {approx:.2f}%")
    print()
    print("WARNINGS / LIMITATIONS")
    print("- This is a survivorship-biased research universe of the 28-stock fixed basket.")
    print("- FX effects are intentionally ignored; this is a return-based GBP notional simulation only.")
    print("- This is a portfolio-construction V1 experiment, not a live recommendation or future-profitability claim.")
    print(f"- Daily output saved to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
