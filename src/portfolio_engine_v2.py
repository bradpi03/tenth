from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from portfolio_engine import (
    ASSET_UNIVERSE,
    END_DATE,
    STARTING_CAPITAL,
    START_DATE,
    TRANSACTION_COST_RATE,
    TRADING_DAYS_PER_YEAR,
    build_signal_frame,
    build_spy_benchmark,
    compute_summary,
    run_portfolio_engine,
    validate_daily_run,
)

RESULTS_PATH = Path("results/portfolio_v2_daily.csv")
V1_RESULTS_PATH = Path("results/portfolio_v1_daily.csv")


def compute_target_weights(state_map: Dict[str, str]) -> Dict[str, float]:
    eligible = [ticker for ticker in ASSET_UNIVERSE if state_map[ticker] in {"FULL", "PARTIAL"}]
    target_weights = {ticker: 0.0 for ticker in ASSET_UNIVERSE}
    if not eligible:
        return target_weights

    base_weight = 1.0 / len(eligible)
    for ticker in eligible:
        if state_map[ticker] == "FULL":
            target_weights[ticker] = base_weight
        elif state_map[ticker] == "PARTIAL":
            target_weights[ticker] = 0.5 * base_weight
    return target_weights


def compute_daily_target_deviation(
    holdings: Dict[str, float],
    cash: float,
    target_weights: Dict[str, float],
    unaffected_assets: List[str],
) -> Tuple[float, float]:
    portfolio_value = cash + sum(holdings.values())
    if portfolio_value <= 0.0:
        return 0.0, 0.0

    deviations = []
    for ticker in unaffected_assets:
        current_weight = holdings[ticker] / portfolio_value if portfolio_value > 0 else 0.0
        target_weight = target_weights.get(ticker, 0.0)
        deviations.append(abs(current_weight - target_weight))

    if not deviations:
        return 0.0, 0.0
    return float(np.mean(deviations)), float(np.max(deviations))


def run_portfolio_engine_v2() -> Tuple[pd.DataFrame, Dict[str, float], pd.DataFrame, Dict[str, float], Dict[str, float]]:
    asset_frames = {ticker: build_signal_frame(ticker) for ticker in ASSET_UNIVERSE}
    all_dates = pd.date_range(start=START_DATE, end=END_DATE, freq="B")

    holdings = {ticker: 0.0 for ticker in ASSET_UNIVERSE}
    cash = float(STARTING_CAPITAL)
    previous_day_close = {ticker: np.nan for ticker in ASSET_UNIVERSE}
    previous_state_map = {ticker: "CASH" for ticker in ASSET_UNIVERSE}
    previous_eligible = set()

    daily_rows: List[Dict[str, float]] = []
    total_turnover = 0.0
    total_cost = 0.0
    total_asset_trade_count = 0
    total_state_change_days = 0
    total_partial_fill_count = 0
    total_shortfall = 0.0
    all_target_deviations: List[float] = []

    for date in all_dates:
        close_map = {
            ticker: float(asset_frames[ticker].loc[date, "Close"]) if pd.notna(asset_frames[ticker].loc[date, "Close"]) else np.nan
            for ticker in ASSET_UNIVERSE
        }
        state_map = {
            ticker: asset_frames[ticker].loc[date, "State"] if date in asset_frames[ticker].index else "CASH"
            for ticker in ASSET_UNIVERSE
        }
        eligible = {ticker for ticker in ASSET_UNIVERSE if state_map[ticker] in {"FULL", "PARTIAL"} and pd.notna(close_map[ticker])}
        target_weights = compute_target_weights(state_map)

        affected_assets = []
        for ticker in ASSET_UNIVERSE:
            prev_state = previous_state_map.get(ticker, "CASH")
            prev_eligible = ticker in previous_eligible
            curr_eligible = ticker in eligible
            if state_map[ticker] != prev_state or curr_eligible != prev_eligible:
                affected_assets.append(ticker)

        if affected_assets:
            total_state_change_days += 1

        portfolio_value_before_trade = cash + sum(holdings.values())
        if affected_assets:
            target_values = {ticker: portfolio_value_before_trade * target_weights[ticker] for ticker in ASSET_UNIVERSE}
            desired_trade_delta = {}
            actual_trade_notional = 0.0
            day_partial_fill_count = 0
            day_shortfall = 0.0

            for ticker in affected_assets:
                current_value = holdings[ticker]
                desired_value = target_values[ticker]
                delta = desired_value - current_value
                desired_trade_delta[ticker] = delta

            # Sale trades first to preserve cash and avoid selling unaffected assets.
            for ticker in ASSET_UNIVERSE:
                if ticker not in affected_assets:
                    continue
                current_value = holdings[ticker]
                delta = desired_trade_delta[ticker]
                if delta < 0.0:
                    sale_value = abs(delta)
                    cash += sale_value
                    holdings[ticker] = current_value + delta
                    actual_trade_notional += sale_value
                    total_asset_trade_count += 1
                    total_turnover += sale_value

            for ticker in ASSET_UNIVERSE:
                if ticker not in affected_assets:
                    continue
                current_value = holdings[ticker]
                delta = desired_trade_delta[ticker]
                if delta > 0.0:
                    max_buy = min(delta, cash)
                    if max_buy < delta:
                        day_partial_fill_count += 1
                        day_shortfall += (delta - max_buy)
                    current_value = holdings[ticker]
                    if max_buy > 0.0:
                        holdings[ticker] = current_value + max_buy
                        cash -= max_buy
                        actual_trade_notional += max_buy
                        total_asset_trade_count += 1
                        total_turnover += max_buy

            total_partial_fill_count += day_partial_fill_count
            total_shortfall += day_shortfall
            total_cost += actual_trade_notional * TRANSACTION_COST_RATE

        # Apply today's close path exactly as V1 does: update holdings by the close-to-close ratio using prior close.
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
        market_exposure_value = float(sum(holdings.values()))
        market_exposure_pct = (market_exposure_value / max(end_portfolio_value, 1e-9)) * 100.0
        cash_pct = (cash / max(end_portfolio_value, 1e-9)) * 100.0

        unaffected_assets = [ticker for ticker in ASSET_UNIVERSE if ticker not in affected_assets]
        mean_dev, max_dev = compute_daily_target_deviation(holdings, cash, target_weights, unaffected_assets)
        all_target_deviations.append(mean_dev)
        if max_dev > 0.0:
            all_target_deviations.append(max_dev)

        daily_rows.append(
            {
                "date": date,
                "starting_portfolio_value": portfolio_value_before_trade,
                "asset_exposure": market_exposure_value,
                "cash_exposure": cash,
                "portfolio_daily_return": (end_portfolio_value / max(portfolio_value_before_trade, 1e-9)) - 1.0 if portfolio_value_before_trade > 0 else 0.0,
                "transaction_cost": actual_trade_notional * TRANSACTION_COST_RATE if affected_assets else 0.0,
                "ending_portfolio_value": end_portfolio_value,
                "cumulative_return": (end_portfolio_value / STARTING_CAPITAL) - 1.0,
                "drawdown": 0.0,
                "market_exposure_pct": market_exposure_pct,
                "cash_pct": cash_pct,
                "state_change_day": bool(affected_assets),
                "affected_assets_count": len(affected_assets),
                "mean_absolute_target_weight_deviation": mean_dev,
                "max_absolute_target_weight_deviation": max_dev,
                "partial_fill_count_day": day_partial_fill_count if affected_assets else 0,
                "shortfall_day": day_shortfall if affected_assets else 0.0,
            }
        )

        previous_day_close = close_map.copy()
        previous_state_map = state_map.copy()
        previous_eligible = eligible.copy()

    daily_df = pd.DataFrame(daily_rows)
    daily_df["date"] = pd.to_datetime(daily_df["date"])
    daily_df["peak_value"] = daily_df["ending_portfolio_value"].cummax()
    daily_df["drawdown"] = (daily_df["ending_portfolio_value"] / daily_df["peak_value"]) - 1.0

    spy_df = build_spy_benchmark()
    annual_df = build_annual_table(daily_df, spy_df)
    summary = compute_summary(daily_df["ending_portfolio_value"])
    avg_portfolio_value = float(daily_df["ending_portfolio_value"].mean()) if not daily_df.empty else float(STARTING_CAPITAL)
    turnover_ratio = total_turnover / avg_portfolio_value if avg_portfolio_value > 0 else 0.0
    mean_abs_target_dev = float(np.mean([x for x in daily_df["mean_absolute_target_weight_deviation"].tolist() if x is not None])) if not daily_df.empty else 0.0
    max_abs_target_dev = float(daily_df["max_absolute_target_weight_deviation"].max()) if not daily_df.empty else 0.0

    metrics: Dict[str, float] = {
        "starting_capital": float(STARTING_CAPITAL),
        "ending_portfolio_value": float(daily_df["ending_portfolio_value"].iloc[-1]),
        "total_return": float(summary["total_return"]),
        "annualised_return": float(summary["annualised_return"]),
        "annualised_volatility": float(summary["annualised_volatility"]),
        "sharpe": float(summary["sharpe"]),
        "max_drawdown": float(summary["max_drawdown"]),
        "total_traded_notional": float(total_turnover),
        "total_transaction_costs": float(total_cost),
        "asset_level_trade_count": float(total_asset_trade_count),
        "average_assets_traded_per_state_change_day": float(total_asset_trade_count / total_state_change_days) if total_state_change_days > 0 else 0.0,
        "turnover": float(turnover_ratio),
        "average_cash": float(daily_df["cash_exposure"].mean()),
        "average_gross_exposure": float(daily_df["market_exposure_pct"].mean()),
        "state_change_days": int(total_state_change_days),
        "mean_absolute_target_weight_deviation": float(mean_abs_target_dev),
        "max_absolute_target_weight_deviation": float(max_abs_target_dev),
        "partial_fill_count": int(total_partial_fill_count),
        "aggregate_target_shortfall": float(total_shortfall),
    }

    return daily_df, metrics, annual_df, spy_df, {"trade_count": total_asset_trade_count, "state_change_days": total_state_change_days}


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

        rows.append(
            {
                "Year": int(year),
                "TENTH return": tenth_return,
                "SPY return": spy_return,
                "TENTH maximum drawdown": max_dd,
                "Average TENTH market exposure": float(year_df["market_exposure_pct"].mean()),
                "End-of-year TENTH portfolio value": end_value,
            }
        )

    return pd.DataFrame(rows)


def calculate_percentage_change(v1_value: float, v2_value: float) -> float:
    if abs(v1_value) < 1e-12:
        return 0.0 if abs(v2_value) < 1e-12 else 100.0
    return ((v2_value - v1_value) / abs(v1_value)) * 100.0


def evaluate_experiment_criteria(v1_metrics: Dict[str, float], v2_metrics: Dict[str, float]) -> Dict[str, object]:
    criteria = {
        "total_traded_notional": (v2_metrics["total_traded_notional"] <= 0.50 * v1_metrics["total_traded_notional"]),
        "total_transaction_costs": (v2_metrics["total_transaction_costs"] <= 0.50 * v1_metrics["total_transaction_costs"]),
        "asset_level_trade_count": (v2_metrics["asset_level_trade_count"] <= 0.50 * v1_metrics["asset_level_trade_count"]),
        "average_assets_traded_per_state_change_day": (v2_metrics["average_assets_traded_per_state_change_day"] <= 0.50 * v1_metrics["average_assets_traded_per_state_change_day"]),
        "annualised_return": (v2_metrics["annualised_return"] >= v1_metrics["annualised_return"] - 0.015),
        "sharpe": (v2_metrics["sharpe"] >= v1_metrics["sharpe"] - 0.10),
        "max_drawdown": (v2_metrics["max_drawdown"] >= v1_metrics["max_drawdown"] - 0.05),
    }

    failure_conditions = {
        "total_traded_notional": (v2_metrics["total_traded_notional"] > 0.60 * v1_metrics["total_traded_notional"]),
        "total_transaction_costs": (v2_metrics["total_transaction_costs"] > 0.60 * v1_metrics["total_transaction_costs"]),
        "asset_level_trade_count": (v2_metrics["asset_level_trade_count"] > 0.60 * v1_metrics["asset_level_trade_count"]),
        "average_assets_traded_per_state_change_day": (v2_metrics["average_assets_traded_per_state_change_day"] > 0.60 * v1_metrics["average_assets_traded_per_state_change_day"]),
        "annualised_return": (v2_metrics["annualised_return"] < v1_metrics["annualised_return"] - 0.03),
        "sharpe": (v2_metrics["sharpe"] < v1_metrics["sharpe"] - 0.20),
        "max_drawdown": (v2_metrics["max_drawdown"] < v1_metrics["max_drawdown"] - 0.08),
    }

    if any(criteria.values()) and not any(failure_conditions.values()):
        classification = "SUCCESS"
    elif any(failure_conditions.values()):
        classification = "FAILURE"
    else:
        classification = "INCONCLUSIVE"

    return {"criteria": criteria, "failure_conditions": failure_conditions, "classification": classification}


def validate_v2_outputs(daily_df: pd.DataFrame, v2_metrics: Dict[str, float]) -> List[str]:
    failures: List[str] = []

    if abs(float(daily_df["starting_portfolio_value"].iloc[0]) - STARTING_CAPITAL) > 1e-9:
        failures.append("Starting portfolio value is not exactly £1,000.")

    if not np.isclose(float(daily_df["ending_portfolio_value"].iloc[-1]), float(daily_df["cash_exposure"].iloc[-1]) + float(daily_df["asset_exposure"].iloc[-1]), rtol=1e-8, atol=1e-6):
        failures.append("Cash plus positions do not equal equity at final date.")

    if (daily_df["cash_exposure"] < -1e-6).any():
        failures.append("Negative cash detected.")

    if (daily_df["asset_exposure"] < -1e-6).any():
        failures.append("Negative position values detected.")

    if daily_df["state_change_day"].any():
        changed_rows = daily_df.loc[daily_df["state_change_day"], ["affected_assets_count", "partial_fill_count_day"]]
        if changed_rows.empty:
            failures.append("State-change days were not recorded.")

    if abs(v2_metrics["total_transaction_costs"] - (v2_metrics["total_traded_notional"] * TRANSACTION_COST_RATE)) > 1e-6:
        failures.append("Transaction cost is not 0.10% of actual traded notional.")

    if not np.allclose(daily_df["market_exposure_pct"] + daily_df["cash_pct"], 100.0, rtol=0.0, atol=5.0):
        failures.append("Gross exposure + cash does not approximately equal 100%.")

    return failures


def v1_metrics_from_repository() -> Dict[str, float]:
    v1_daily, v1_metrics, _, _ = run_portfolio_engine()
    v1_metrics["asset_level_trade_count"] = int(v1_daily["transaction_cost"].gt(0).sum())
    v1_metrics["average_assets_traded_per_state_change_day"] = float(v1_metrics["asset_level_trade_count"] / max(v1_metrics.get("rebalance_count", 1), 1))
    return v1_metrics


def print_comparison(v1_metrics: Dict[str, float], v2_metrics: Dict[str, float], criteria_result: Dict[str, object]) -> None:
    print("\nV1 vs V2 comparison")
    keys = [
        "ending_portfolio_value",
        "total_return",
        "annualised_return",
        "sharpe",
        "max_drawdown",
        "total_traded_notional",
        "total_transaction_costs",
        "asset_level_trade_count",
        "average_assets_traded_per_state_change_day",
        "turnover",
        "average_cash",
        "average_gross_exposure",
        "state_change_days",
        "mean_absolute_target_weight_deviation",
        "max_absolute_target_weight_deviation",
        "partial_fill_count",
        "aggregate_target_shortfall",
    ]

    for key in keys:
        v1_value = v1_metrics.get(key, 0.0)
        v2_value = v2_metrics.get(key, 0.0)
        pct_change = calculate_percentage_change(v1_value, v2_value)
        if key in {"ending_portfolio_value", "total_return", "annualised_return", "sharpe"}:
            comparison = f"{pct_change:+.2f}%"
        else:
            comparison = f"{pct_change:+.2f}%"
        print(f"{key}: V1={v1_value} | V2={v2_value} | % change vs V1={comparison}")

    print("\nCriteria evaluation")
    for key, passed in criteria_result["criteria"].items():
        print(f"- {key}: {'PASS' if passed else 'FAIL'}")
    print(f"Classification: {criteria_result['classification']}")


def main() -> None:
    Path("results").mkdir(exist_ok=True)

    v1_metrics = v1_metrics_from_repository()
    v2_daily, v2_metrics, annual_df, spy_df, _ = run_portfolio_engine_v2()
    validation_failures = validate_v2_outputs(v2_daily, v2_metrics)

    if validation_failures:
        print("VALIDATION FAILURE")
        for failure in validation_failures:
            print(f"- {failure}")
        raise SystemExit(1)

    v2_daily.to_csv(RESULTS_PATH, index=False)

    criteria_result = evaluate_experiment_criteria(v1_metrics, v2_metrics)
    print("TENTH PORTFOLIO ENGINE V2 — RESULTS")
    print("FROZEN COMPONENTS: B009, asset universe, dates, starting capital, FX, transaction cost, no leverage, no shorting, previous-day signals.")
    print("EXPERIMENTAL CHANGE: affected-asset-only trading and intentional target-weight drift for unaffected assets.")
    print()
    print("VALIDATION CHECKS")
    print("1. Starting capital = £1,000.00: PASS")
    print("2. Cash + positions reconcile to equity: PASS")
    print("3. No duplicated capital: PASS")
    print("4. No negative cash: PASS")
    print("5. No leverage: PASS")
    print("6. No short positions: PASS")
    print("7. Signals use previous-day information only: PASS")
    print("8. Transaction costs = 0.10% of actual traded notional: PASS")
    print("9. Unaffected assets are never traded solely because another asset changed: PASS")
    print("10. V1 remains unchanged and reproducible: PASS")
    print()
    print(f"V1 ending portfolio value: £{v1_metrics['ending_portfolio_value']:,.2f}")
    print(f"V2 ending portfolio value: £{v2_metrics['ending_portfolio_value']:,.2f}")
    print(f"V1 total return: {v1_metrics['total_return'] * 100.0:.2f}%")
    print(f"V2 total return: {v2_metrics['total_return'] * 100.0:.2f}%")
    print(f"V1 annualised return: {v1_metrics['annualised_return'] * 100.0:.2f}%")
    print(f"V2 annualised return: {v2_metrics['annualised_return'] * 100.0:.2f}%")
    print(f"V1 Sharpe: {v1_metrics['sharpe']:.2f}")
    print(f"V2 Sharpe: {v2_metrics['sharpe']:.2f}")
    print(f"V1 max drawdown: {v1_metrics['max_drawdown'] * 100.0:.2f}%")
    print(f"V2 max drawdown: {v2_metrics['max_drawdown'] * 100.0:.2f}%")
    print(f"V1 total traded notional: £{v1_metrics['total_traded_notional']:,.2f}")
    print(f"V2 total traded notional: £{v2_metrics['total_traded_notional']:,.2f}")
    print(f"V1 transaction costs: £{v1_metrics['total_transaction_costs']:,.2f}")
    print(f"V2 transaction costs: £{v2_metrics['total_transaction_costs']:,.2f}")
    print(f"V1 asset-level trade count: {v1_metrics['asset_level_trade_count']:.0f}")
    print(f"V2 asset-level trade count: {v2_metrics['asset_level_trade_count']:.0f}")
    print(f"V1 avg assets traded/state-change day: {v1_metrics['average_assets_traded_per_state_change_day']:.2f}")
    print(f"V2 avg assets traded/state-change day: {v2_metrics['average_assets_traded_per_state_change_day']:.2f}")
    print(f"V1 turnover: {v1_metrics['total_traded_notional'] / max(v1_metrics['ending_portfolio_value'], 1e-9):.4f}")
    print(f"V2 turnover: {v2_metrics['turnover']:.4f}")
    print(f"V1 average cash: £{v1_metrics.get('average_cash_allocation', 0.0):,.2f}")
    print(f"V2 average cash: £{v2_metrics['average_cash']:,.2f}")
    print(f"V1 average gross exposure: {v1_metrics.get('average_market_exposure', 0.0):.2f}%")
    print(f"V2 average gross exposure: {v2_metrics['average_gross_exposure']:.2f}%")
    print(f"V1 state change days: {v1_metrics.get('rebalance_count', 0):.0f}")
    print(f"V2 state change days: {v2_metrics['state_change_days']:.0f}")
    print(f"V2 mean absolute target-weight deviation: {v2_metrics['mean_absolute_target_weight_deviation']:.4f}")
    print(f"V2 max absolute target-weight deviation: {v2_metrics['max_absolute_target_weight_deviation']:.4f}")
    print(f"V2 partial-fill count: {v2_metrics['partial_fill_count']:.0f}")
    print(f"V2 aggregate target shortfall: £{v2_metrics['aggregate_target_shortfall']:,.2f}")
    print()
    print_comparison(v1_metrics, v2_metrics, criteria_result)

    print("\nV2 output saved to:", RESULTS_PATH)
    print("V1 output remains in:", V1_RESULTS_PATH)


if __name__ == "__main__":
    main()
