import numpy as np
import pandas as pd
import yfinance as yf


STARTING_CAPITAL = 1000.0
ENTRY_COST = 0.001
EXIT_COST = 0.001
TRADING_DAYS_PER_YEAR = 252
RISK_FREE_RATE = 0.0
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "JPM", "XOM", "SPY"]


def compute_summary(values):
    if values.empty:
        return {
            "total_return": 0.0,
            "annualised_return": 0.0,
            "annualised_volatility": 0.0,
            "max_drawdown": 0.0,
            "sharpe": 0.0,
        }

    start_value = values.iloc[0]
    end_value = values.iloc[-1]
    total_return = (end_value / start_value) - 1.0

    periods = len(values) / TRADING_DAYS_PER_YEAR
    annualised_return = (
        (1.0 + total_return) ** (1.0 / periods) - 1.0
        if periods > 0 and total_return > -1.0
        else 0.0
    )

    daily_returns = values.pct_change().dropna()
    annualised_volatility = (
        daily_returns.std(ddof=1) * np.sqrt(TRADING_DAYS_PER_YEAR)
        if len(daily_returns) > 1
        else 0.0
    )

    peak_values = values.cummax()
    max_drawdown = float(((values / peak_values) - 1.0).min()) if not values.empty else 0.0
    sharpe = (
        (annualised_return - RISK_FREE_RATE) / annualised_volatility
        if annualised_volatility > 0
        else 0.0
    )

    return {
        "total_return": total_return,
        "annualised_return": annualised_return,
        "annualised_volatility": annualised_volatility,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
    }


def compute_trade_metrics(df):
    trade_returns = []
    previous_position = 0
    entry_price = None

    for _, row in df.iterrows():
        current_position = int(row["Position"])

        if previous_position == 0 and current_position == 1:
            entry_price = float(row["Close"])
        elif previous_position == 1 and current_position == 0:
            if entry_price is None:
                previous_position = current_position
                continue

            exit_price = float(row["Close"])
            trade_return = ((exit_price / entry_price) - 1.0) - ENTRY_COST - EXIT_COST
            trade_returns.append(trade_return)
            entry_price = None

        previous_position = current_position

    if not trade_returns:
        return 0, 0.0, 0.0, 0.0

    trade_returns = np.array(trade_returns, dtype=float)
    winning_trades = trade_returns[trade_returns > 0]
    losing_trades = trade_returns[trade_returns < 0]

    completed_trades = len(trade_returns)
    win_rate = len(winning_trades) / completed_trades if completed_trades else 0.0
    average_winning_trade = winning_trades.mean() if len(winning_trades) else 0.0
    average_losing_trade = losing_trades.mean() if len(losing_trades) else 0.0

    return completed_trades, win_rate, average_winning_trade, average_losing_trade


def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def run_backtest_003_for_ticker(ticker):
    data = yf.download(
        ticker,
        period="5y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"][ticker]
    else:
        close = data["Close"]

    df = pd.DataFrame({"Close": close}).dropna().copy()
    df["Buy_Hold_Value"] = STARTING_CAPITAL * (1.0 + df["Close"].pct_change().fillna(0)).cumprod()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["Trend_Signal"] = (df["SMA20"] > df["SMA50"]).astype(int)
    df["RSI14"] = calculate_rsi(df["Close"], period=14)
    df["RSI_Above_50"] = (df["RSI14"] > 50).astype(int)
    df["Market_Return"] = df["Close"].pct_change()

    # Exact Backtest 003 strategy rules (no tuning):
    # Use the previous day's signal to avoid look-ahead bias.
    # Entry: enter long when the previous day's SMA20 > SMA50 and RSI(14) > 50.
    # Exit: exit when the previous day's trend is no longer bullish OR RSI(14) <= 50.
    df["Position"] = (
        (df["Trend_Signal"].shift(1) == 1) &
        (df["RSI_Above_50"].shift(1) == 1)
    ).astype(int)
    df["Entry_Trade"] = ((df["Position"].shift(1).fillna(0) == 0) & (df["Position"] == 1)).astype(float)
    df["Exit_Trade"] = ((df["Position"].shift(1).fillna(0) == 1) & (df["Position"] == 0)).astype(float)
    df["Strategy_Return"] = (
        df["Position"] * df["Market_Return"]
        - ENTRY_COST * df["Entry_Trade"]
        - EXIT_COST * df["Exit_Trade"]
    )

    df = df.dropna(subset=["Market_Return", "Strategy_Return"]).copy()
    df["Strategy_Value"] = STARTING_CAPITAL * (1.0 + df["Strategy_Return"]).cumprod()

    buy_hold_summary = compute_summary(df["Buy_Hold_Value"])
    strategy_summary = compute_summary(df["Strategy_Value"])
    completed_trades, win_rate, avg_win, avg_loss = compute_trade_metrics(df)
    market_exposure = df["Position"].mean() * 100.0

    return {
        "ticker": ticker,
        "buy_hold_total_return": buy_hold_summary["total_return"],
        "strategy_total_return": strategy_summary["total_return"],
        "annualised_strategy_return": strategy_summary["annualised_return"],
        "annualised_strategy_volatility": strategy_summary["annualised_volatility"],
        "max_strategy_drawdown": strategy_summary["max_drawdown"],
        "strategy_sharpe": strategy_summary["sharpe"],
        "completed_trades": completed_trades,
        "win_rate": win_rate,
        "market_exposure": market_exposure,
        "buy_hold_sharpe": buy_hold_summary["sharpe"],
        "buy_hold_annualised_return": buy_hold_summary["annualised_return"],
        "buy_hold_max_drawdown": buy_hold_summary["max_drawdown"],
    }


def main():
    print("\nTENTH — BACKTEST 004")
    print("CROSS-ASSET VALIDATION")
    print(f"Starting capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Transaction cost: {ENTRY_COST * 100:.2f}% entry / {EXIT_COST * 100:.2f}% exit")
    print("Data: 5 years of daily data")
    print("Strategy: exact Backtest 003 rules with no tuning")

    results = [run_backtest_003_for_ticker(ticker) for ticker in TICKERS]

    print("\nASSET RESULTS")
    for result in results:
        print(f"\n{result['ticker']}")
        print(f"  Buy & Hold total return: {(result['buy_hold_total_return'] * 100):.2f}%")
        print(f"  TENTH 003 total return: {(result['strategy_total_return'] * 100):.2f}%")
        print(f"  Annualised strategy return: {(result['annualised_strategy_return'] * 100):.2f}%")
        print(f"  Annualised strategy volatility: {(result['annualised_strategy_volatility'] * 100):.2f}%")
        print(f"  Maximum strategy drawdown: {(result['max_strategy_drawdown'] * 100):.2f}%")
        print(f"  Strategy Sharpe ratio: {result['strategy_sharpe']:.2f}")
        print(f"  Completed trades: {result['completed_trades']}")
        print(f"  Win rate: {result['win_rate'] * 100:.2f}%")
        print(f"  Market exposure: {result['market_exposure']:.1f}%")

    positive_returns = sum(1 for r in results if r["strategy_total_return"] > 0)
    beat_bh = sum(1 for r in results if r["strategy_total_return"] > r["buy_hold_total_return"])
    higher_sharpe = sum(1 for r in results if r["strategy_sharpe"] > r["buy_hold_sharpe"])
    lower_drawdown = sum(1 for r in results if r["max_strategy_drawdown"] < r["buy_hold_max_drawdown"])
    annual_returns = [r["annualised_strategy_return"] for r in results]
    sharpe_values = [r["strategy_sharpe"] for r in results]

    print("\nAGGREGATE SUMMARY")
    print(f"Positive TENTH returns: {positive_returns} / {len(results)}")
    print(f"TENTH beat Buy & Hold: {beat_bh} / {len(results)}")
    print(f"TENTH higher Sharpe than Buy & Hold: {higher_sharpe} / {len(results)}")
    print(f"TENTH smaller max drawdown than Buy & Hold: {lower_drawdown} / {len(results)}")
    print(f"Median TENTH annualised return: {np.median(annual_returns) * 100:.2f}%")
    print(f"Median TENTH Sharpe ratio: {np.median(sharpe_values):.2f}")

    print("\nStrategy rules retained exactly:")
    print("Entry: use the previous day's signal and enter long when SMA20 > SMA50 and RSI(14) > 50")
    print("Exit: use the previous day's signal and exit when the trend is no longer bullish OR RSI(14) <= 50")


if __name__ == "__main__":
    main()