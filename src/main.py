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


def build_backtest_003(df):
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["Trend_Signal"] = (df["SMA20"] > df["SMA50"]).astype(int)
    df["RSI14"] = calculate_rsi(df["Close"], period=14)
    df["RSI_Above_50"] = (df["RSI14"] > 50).astype(int)
    df["Market_Return"] = df["Close"].pct_change()

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

    # Backtest 003 uses the original exit rule: the prior day's trend must still be bullish,
    # or RSI(14) must still be above 50; otherwise exit.
    df["Position"] = (
        ((df["Trend_Signal"].shift(1) == 1) & (df["RSI_Above_50"].shift(1) == 1))
        .astype(int)
    )
    df["Exit_Trade"] = (
        ((df["Trend_Signal"].shift(1) == 0) | (df["RSI_Above_50"].shift(1) == 0))
        & (df["Position"].shift(1).fillna(0) == 1)
    ).astype(float)
    df["Strategy_Return"] = (
        df["Position"] * df["Market_Return"]
        - ENTRY_COST * df["Entry_Trade"]
        - EXIT_COST * df["Exit_Trade"]
    )

    df = df.dropna(subset=["Market_Return", "Strategy_Return"]).copy()
    df["Strategy_Value"] = STARTING_CAPITAL * (1.0 + df["Strategy_Return"]).cumprod()
    return df


def build_backtest_005(df):
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["Trend_Signal"] = (df["SMA20"] > df["SMA50"]).astype(int)
    df["RSI14"] = calculate_rsi(df["Close"], period=14)
    df["RSI_Above_50"] = (df["RSI14"] > 50).astype(int)
    df["Market_Return"] = df["Close"].pct_change()

    # Backtest 005 keeps the same entry as 003, but exits only when the trend fails.
    # RSI is used as an entry confirmation only and not as an exit trigger.
    positions = np.zeros(len(df), dtype=int)
    prev_position = 0
    for i in range(len(df)):
        trend_prev = df["Trend_Signal"].iloc[i - 1] if i > 0 else 0
        rsi_prev = df["RSI_Above_50"].iloc[i - 1] if i > 0 else 0

        if prev_position == 1:
            if trend_prev == 0:
                positions[i] = 0
            else:
                positions[i] = 1
        else:
            positions[i] = 1 if (trend_prev == 1 and rsi_prev == 1) else 0

        prev_position = positions[i]

    df["Position"] = positions
    df["Entry_Trade"] = ((df["Position"].shift(1).fillna(0) == 0) & (df["Position"] == 1)).astype(float)
    df["Exit_Trade"] = ((df["Position"].shift(1).fillna(0) == 1) & (df["Position"] == 0)).astype(float)
    df["Strategy_Return"] = (
        df["Position"] * df["Market_Return"]
        - ENTRY_COST * df["Entry_Trade"]
        - EXIT_COST * df["Exit_Trade"]
    )

    df = df.dropna(subset=["Market_Return", "Strategy_Return"]).copy()
    df["Strategy_Value"] = STARTING_CAPITAL * (1.0 + df["Strategy_Return"]).cumprod()
    return df


def build_backtest_006(df):
    df = df.copy()
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()
    df["SMA200"] = df["Close"].rolling(200).mean()
    df["Trend_Signal"] = (df["SMA20"] > df["SMA50"]).astype(int)
    df["RSI14"] = calculate_rsi(df["Close"], period=14)
    df["RSI_Above_50"] = (df["RSI14"] > 50).astype(int)
    df["Above_SMA200"] = (df["Close"] > df["SMA200"]).astype(int)
    df["Market_Return"] = df["Close"].pct_change()

    # Backtest 006 entry: use previous-day values for all three filters.
    # Entry: SMA20 > SMA50 AND RSI(14) > 50 AND Close > SMA200.
    # Exit: original Backtest 003 exit logic — exit when trend fails OR RSI <= 50.
    positions = np.zeros(len(df), dtype=int)
    prev_position = 0
    for i in range(len(df)):
        trend_prev = df["Trend_Signal"].iloc[i - 1] if i > 0 else 0
        rsi_prev = df["RSI_Above_50"].iloc[i - 1] if i > 0 else 0
        above_200_prev = df["Above_SMA200"].iloc[i - 1] if i > 0 else 0

        if prev_position == 1:
            exit_signal = (trend_prev == 0) or (rsi_prev == 0)
            positions[i] = 0 if exit_signal else 1
        else:
            positions[i] = 1 if ((trend_prev == 1) and (rsi_prev == 1) and (above_200_prev == 1)) else 0

        prev_position = positions[i]

    df["Position"] = positions
    df["Entry_Trade"] = ((df["Position"].shift(1).fillna(0) == 0) & (df["Position"] == 1)).astype(float)
    df["Exit_Trade"] = ((df["Position"].shift(1).fillna(0) == 1) & (df["Position"] == 0)).astype(float)
    df["Strategy_Return"] = (
        df["Position"] * df["Market_Return"]
        - ENTRY_COST * df["Entry_Trade"]
        - EXIT_COST * df["Exit_Trade"]
    )

    df = df.dropna(subset=["Market_Return", "Strategy_Return"]).copy()
    df["Strategy_Value"] = STARTING_CAPITAL * (1.0 + df["Strategy_Return"]).cumprod()
    return df


def evaluate_ticker(ticker):
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

    b003_df = build_backtest_003(df)
    b005_df = build_backtest_005(df)
    b006_df = build_backtest_006(df)

    buy_hold_summary = compute_summary(df["Buy_Hold_Value"])
    b003_summary = compute_summary(b003_df["Strategy_Value"])
    b005_summary = compute_summary(b005_df["Strategy_Value"])
    b006_summary = compute_summary(b006_df["Strategy_Value"])

    b003_trades, b003_win, b003_avg_win, b003_avg_loss = compute_trade_metrics(b003_df)
    b005_trades, b005_win, b005_avg_win, b005_avg_loss = compute_trade_metrics(b005_df)
    b006_trades, b006_win, b006_avg_win, b006_avg_loss = compute_trade_metrics(b006_df)

    return {
        "ticker": ticker,
        "buy_hold_total_return": buy_hold_summary["total_return"],
        "buy_hold_sharpe": buy_hold_summary["sharpe"],
        "buy_hold_max_drawdown": buy_hold_summary["max_drawdown"],
        "b003_total_return": b003_summary["total_return"],
        "b003_annualised_return": b003_summary["annualised_return"],
        "b003_annualised_volatility": b003_summary["annualised_volatility"],
        "b003_max_drawdown": b003_summary["max_drawdown"],
        "b003_sharpe": b003_summary["sharpe"],
        "b003_trades": b003_trades,
        "b003_win_rate": b003_win,
        "b003_avg_win": b003_avg_win,
        "b003_avg_loss": b003_avg_loss,
        "b003_market_exposure": b003_df["Position"].mean() * 100.0,
        "b005_total_return": b005_summary["total_return"],
        "b005_annualised_return": b005_summary["annualised_return"],
        "b005_annualised_volatility": b005_summary["annualised_volatility"],
        "b005_max_drawdown": b005_summary["max_drawdown"],
        "b005_sharpe": b005_summary["sharpe"],
        "b005_trades": b005_trades,
        "b005_win_rate": b005_win,
        "b005_avg_win": b005_avg_win,
        "b005_avg_loss": b005_avg_loss,
        "b005_market_exposure": b005_df["Position"].mean() * 100.0,
        "b006_total_return": b006_summary["total_return"],
        "b006_annualised_return": b006_summary["annualised_return"],
        "b006_annualised_volatility": b006_summary["annualised_volatility"],
        "b006_max_drawdown": b006_summary["max_drawdown"],
        "b006_sharpe": b006_summary["sharpe"],
        "b006_trades": b006_trades,
        "b006_win_rate": b006_win,
        "b006_avg_win": b006_avg_win,
        "b006_avg_loss": b006_avg_loss,
        "b006_market_exposure": b006_df["Position"].mean() * 100.0,
    }


def load_ticker_data(ticker, period="15y"):
    data = yf.download(
        ticker,
        period=period,
        interval="1d",
        auto_adjust=True,
        progress=False,
    )
    if data.empty:
        return pd.DataFrame(columns=["Close"])

    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"][ticker]
    else:
        close = data["Close"]

    df = pd.DataFrame({"Close": close}).dropna().copy()
    return df


def evaluate_ticker_b007(ticker):
    full_df = load_ticker_data(ticker, period="15y")
    if full_df.empty:
        return {
            "ticker": ticker,
            "eligible": False,
            "reason": "no data available after download",
            "b006_start": None,
            "b006_end": None,
            "test_start": None,
            "test_end": None,
            "available_start": None,
            "available_end": None,
        }

    max_date = full_df.index.max().normalize()
    b006_start = (max_date - pd.DateOffset(years=5) + pd.Timedelta(days=1)).normalize()
    b006_end = max_date
    b006_window = full_df.loc[(full_df.index >= b006_start) & (full_df.index <= b006_end)].copy()
    if b006_window.empty:
        return {
            "ticker": ticker,
            "eligible": False,
            "reason": "insufficient data for the Backtest 006 window",
            "b006_start": None,
            "b006_end": None,
            "test_start": None,
            "test_end": None,
            "available_start": full_df.index.min().strftime("%Y-%m-%d"),
            "available_end": full_df.index.max().strftime("%Y-%m-%d"),
        }

    test_start = (b006_start - pd.DateOffset(years=5)).normalize()
    test_end = (b006_start - pd.Timedelta(days=1)).normalize()
    warmup_start = test_start - pd.DateOffset(days=250)
    warmup_df = full_df.loc[(full_df.index >= warmup_start) & (full_df.index <= test_end)].copy()
    test_df = full_df.loc[(full_df.index >= test_start) & (full_df.index <= test_end)].copy()

    if test_df.empty:
        return {
            "ticker": ticker,
            "eligible": False,
            "reason": "no historical data for the preceding five-year period",
            "b006_start": b006_start.strftime("%Y-%m-%d"),
            "b006_end": b006_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "available_start": full_df.index.min().strftime("%Y-%m-%d"),
            "available_end": full_df.index.max().strftime("%Y-%m-%d"),
        }

    if warmup_df.empty or warmup_df.index.min().normalize() > test_start or test_df.index.max().normalize() < test_end:
        return {
            "ticker": ticker,
            "eligible": False,
            "reason": "insufficient data for the full out-of-sample test window",
            "b006_start": b006_start.strftime("%Y-%m-%d"),
            "b006_end": b006_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "available_start": warmup_df.index.min().strftime("%Y-%m-%d") if not warmup_df.empty else full_df.index.min().strftime("%Y-%m-%d"),
            "available_end": test_df.index.max().strftime("%Y-%m-%d") if not test_df.empty else full_df.index.max().strftime("%Y-%m-%d"),
        }

    test_df["Buy_Hold_Value"] = STARTING_CAPITAL * (1.0 + test_df["Close"].pct_change().fillna(0)).cumprod()
    b007_df = build_backtest_006(warmup_df)
    b007_df = b007_df.loc[(b007_df.index >= test_start) & (b007_df.index <= test_end)].copy()

    if b007_df.empty:
        return {
            "ticker": ticker,
            "eligible": False,
            "reason": "no valid strategy observations in the Backtest 007 test window",
            "b006_start": b006_start.strftime("%Y-%m-%d"),
            "b006_end": b006_end.strftime("%Y-%m-%d"),
            "test_start": test_start.strftime("%Y-%m-%d"),
            "test_end": test_end.strftime("%Y-%m-%d"),
            "available_start": warmup_df.index.min().strftime("%Y-%m-%d"),
            "available_end": test_df.index.max().strftime("%Y-%m-%d"),
        }

    buy_hold_summary = compute_summary(test_df["Buy_Hold_Value"])
    strategy_summary = compute_summary(b007_df["Strategy_Value"])
    trades, win_rate, avg_win, avg_loss = compute_trade_metrics(b007_df)

    return {
        "ticker": ticker,
        "eligible": True,
        "b006_start": b006_start.strftime("%Y-%m-%d"),
        "b006_end": b006_end.strftime("%Y-%m-%d"),
        "test_start": test_start.strftime("%Y-%m-%d"),
        "test_end": test_end.strftime("%Y-%m-%d"),
        "buy_hold_total_return": buy_hold_summary["total_return"],
        "buy_hold_annualised_return": buy_hold_summary["annualised_return"],
        "buy_hold_annualised_volatility": buy_hold_summary["annualised_volatility"],
        "buy_hold_max_drawdown": buy_hold_summary["max_drawdown"],
        "buy_hold_sharpe": buy_hold_summary["sharpe"],
        "strategy_total_return": strategy_summary["total_return"],
        "strategy_annualised_return": strategy_summary["annualised_return"],
        "strategy_annualised_volatility": strategy_summary["annualised_volatility"],
        "strategy_max_drawdown": strategy_summary["max_drawdown"],
        "strategy_sharpe": strategy_summary["sharpe"],
        "completed_trades": trades,
        "win_rate": win_rate,
        "average_winning_trade": avg_win,
        "average_losing_trade": avg_loss,
        "market_exposure": b007_df["Position"].mean() * 100.0,
    }


def compute_max_drawdown(values):
    if values.empty:
        return 0.0
    peak = float(values.iloc[0])
    max_drawdown = 0.0
    for value in values:
        value_float = float(value)
        if value_float > peak:
            peak = value_float
        drawdown = (value_float / peak) - 1.0
        if drawdown < max_drawdown:
            max_drawdown = drawdown
    return float(max_drawdown)


def evaluate_b007_drawdown_audit():
    original_results = [evaluate_ticker_b007(ticker) for ticker in TICKERS]
    eligible = [r for r in original_results if r["eligible"]]
    drawdown_smaller_flags = []
    bh_drawdowns = []
    strategy_drawdowns = []

    print("\nPART 1 — AUDIT THE DRAWDOWN CALCULATION")
    for result in eligible:
        test_start = pd.Timestamp(result["test_start"])
        test_end = pd.Timestamp(result["test_end"])
        data = load_ticker_data(result["ticker"], period="15y")
        test_df = data.loc[(data.index >= test_start) & (data.index <= test_end)].copy()
        if test_df.empty:
            continue

        bh_value = STARTING_CAPITAL * (1.0 + test_df["Close"].pct_change().fillna(0)).cumprod()
        warmup_df = data.loc[(data.index >= (test_start - pd.DateOffset(days=250))) & (data.index <= test_end)].copy()
        strategy_df = build_backtest_006(warmup_df)
        strategy_df = strategy_df.loc[(strategy_df.index >= test_start) & (strategy_df.index <= test_end)].copy()

        if strategy_df.empty:
            continue

        bh_dd = compute_max_drawdown(bh_value)
        strategy_dd = compute_max_drawdown(strategy_df["Strategy_Value"])
        drawdown_smaller_flags.append(strategy_dd > bh_dd)
        bh_drawdowns.append(bh_dd)
        strategy_drawdowns.append(strategy_dd)

        print(f"\n{result['ticker']}")
        print(f"  Buy & Hold max drawdown: {(bh_dd * 100):.2f}%")
        print(f"  Strategy max drawdown: {(strategy_dd * 100):.2f}%")
        print(f"  Strategy drawdown smaller than Buy & Hold: {'YES' if strategy_dd > bh_dd else 'NO'}")

    corrected_count = sum(1 for flag in drawdown_smaller_flags if flag)
    median_bh_drawdown = np.median(bh_drawdowns) * 100 if bh_drawdowns else 0.0
    median_strategy_drawdown = np.median(strategy_drawdowns) * 100 if strategy_drawdowns else 0.0

    print(f"\nExact count where strategy drawdown is smaller: {corrected_count} / {len(eligible)}")
    print(f"Median Buy & Hold drawdown: {median_bh_drawdown:.2f}%")
    print(f"Median strategy drawdown: {median_strategy_drawdown:.2f}%")
    print("\nPREVIOUS BACKTEST 007 AGGREGATE COUNT: WRONG = 1 / 8")
    print(f"CORRECTED FIGURE: {corrected_count} / {len(eligible)}")


def evaluate_additional_asset(ticker):
    start_date = pd.Timestamp("2016-08-28")
    end_date = pd.Timestamp("2021-08-27")
    data = load_ticker_data(ticker, period="15y")
    if data.empty:
        return {"ticker": ticker, "eligible": False, "reason": "no data available after download"}

    test_df = data.loc[(data.index >= start_date) & (data.index <= end_date)].copy()
    if test_df.empty:
        return {"ticker": ticker, "eligible": False, "reason": "no data in required out-of-sample window"}

    warmup_start = start_date - pd.DateOffset(days=250)
    warmup_df = data.loc[(data.index >= warmup_start) & (data.index <= end_date)].copy()
    if warmup_df.empty or warmup_df.index.min() > start_date:
        return {"ticker": ticker, "eligible": False, "reason": "insufficient historical data for warm-up and test window"}

    strategy_df = build_backtest_006(warmup_df)
    strategy_df = strategy_df.loc[(strategy_df.index >= start_date) & (strategy_df.index <= end_date)].copy()
    if strategy_df.empty:
        return {"ticker": ticker, "eligible": False, "reason": "no valid strategy observations in test window"}

    bh_value = STARTING_CAPITAL * (1.0 + test_df["Close"].pct_change().fillna(0)).cumprod()
    bh_summary = compute_summary(bh_value)
    strategy_summary = compute_summary(strategy_df["Strategy_Value"])
    trades, win_rate, avg_win, avg_loss = compute_trade_metrics(strategy_df)

    return {
        "ticker": ticker,
        "eligible": True,
        "test_start": start_date.strftime("%Y-%m-%d"),
        "test_end": end_date.strftime("%Y-%m-%d"),
        "buy_hold_total_return": bh_summary["total_return"],
        "buy_hold_annualised_return": bh_summary["annualised_return"],
        "buy_hold_sharpe": bh_summary["sharpe"],
        "buy_hold_max_drawdown": bh_summary["max_drawdown"],
        "strategy_total_return": strategy_summary["total_return"],
        "strategy_annualised_return": strategy_summary["annualised_return"],
        "strategy_sharpe": strategy_summary["sharpe"],
        "strategy_max_drawdown": strategy_summary["max_drawdown"],
        "completed_trades": trades,
        "win_rate": win_rate,
        "average_winning_trade": avg_win,
        "average_losing_trade": avg_loss,
        "market_exposure": strategy_df["Position"].mean() * 100.0,
    }


def main():
    print("\nTENTH — BACKTEST 008 — ROBUSTNESS AUDIT")
    print("Frozen strategy: Backtest 006 rules retained exactly")
    print(f"Starting capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Transaction cost: {ENTRY_COST * 100:.2f}% entry / {EXIT_COST * 100:.2f}% exit")
    print("Out-of-sample window: 2016-08-28 to 2021-08-27")
    print("Strategy: exact Backtest 006 entry/exit logic, no tuning or changes")

    evaluate_b007_drawdown_audit()

    additional_assets = [
        "META", "NFLX", "TSLA", "INTC", "IBM", "CSCO", "ORCL", "WMT",
        "COST", "KO", "PG", "JNJ", "PFE", "CVX", "BAC", "GS", "CAT",
        "BA", "DIS", "GE"
    ]

    print("\nPART 2 — BROADER CROSS-ASSET ROBUSTNESS TEST")
    eligible_assets = []
    ineligible_assets = []
    for ticker in additional_assets:
        result = evaluate_additional_asset(ticker)
        if result["eligible"]:
            eligible_assets.append(result)
            print(f"\n{ticker}")
            print(f"  Test dates: {result['test_start']} to {result['test_end']}")
            print(f"  Buy & Hold total return: {(result['buy_hold_total_return'] * 100):.2f}%")
            print(f"  Strategy total return: {(result['strategy_total_return'] * 100):.2f}%")
            print(f"  Buy & Hold annualised return: {(result['buy_hold_annualised_return'] * 100):.2f}%")
            print(f"  Strategy annualised return: {(result['strategy_annualised_return'] * 100):.2f}%")
            print(f"  Buy & Hold Sharpe: {result['buy_hold_sharpe']:.2f}")
            print(f"  Strategy Sharpe: {result['strategy_sharpe']:.2f}")
            print(f"  Buy & Hold maximum drawdown: {(result['buy_hold_max_drawdown'] * 100):.2f}%")
            print(f"  Strategy maximum drawdown: {(result['strategy_max_drawdown'] * 100):.2f}%")
            print(f"  Completed trades: {result['completed_trades']}")
            print(f"  Win rate: {result['win_rate'] * 100:.2f}%")
            print(f"  Market exposure: {result['market_exposure']:.1f}%")
        else:
            ineligible_assets.append((ticker, result["reason"]))
            print(f"\n{ticker}")
            print(f"  INELIGIBLE: {result['reason']}")

    if eligible_assets:
        positive_returns = sum(1 for r in eligible_assets if r["strategy_total_return"] > 0)
        beat_bh = sum(1 for r in eligible_assets if r["strategy_total_return"] > r["buy_hold_total_return"])
        sharpe_beats = sum(1 for r in eligible_assets if r["strategy_sharpe"] > r["buy_hold_sharpe"])
        dd_smaller = sum(1 for r in eligible_assets if r["strategy_max_drawdown"] > r["buy_hold_max_drawdown"])
        median_strategy_return = np.median([r["strategy_annualised_return"] for r in eligible_assets]) * 100
        median_buy_hold_return = np.median([r["buy_hold_annualised_return"] for r in eligible_assets]) * 100
        median_strategy_sharpe = np.median([r["strategy_sharpe"] for r in eligible_assets])
        median_buy_hold_sharpe = np.median([r["buy_hold_sharpe"] for r in eligible_assets])
        median_strategy_dd = np.median([r["strategy_max_drawdown"] for r in eligible_assets]) * 100
        median_buy_hold_dd = np.median([r["buy_hold_max_drawdown"] for r in eligible_assets]) * 100
        median_market_exposure = np.median([r["market_exposure"] for r in eligible_assets])

        print("\nPART 3 — AGGREGATE ROBUSTNESS SUMMARY")
        print(f"Eligible assets: {len(eligible_assets)}")
        print(f"Positive-return strategy assets: {positive_returns} / {len(eligible_assets)}")
        print(f"Assets where strategy beats Buy & Hold: {beat_bh} / {len(eligible_assets)}")
        print(f"Assets where strategy Sharpe exceeds Buy & Hold: {sharpe_beats} / {len(eligible_assets)}")
        print(f"Assets where strategy max drawdown is smaller than Buy & Hold: {dd_smaller} / {len(eligible_assets)}")
        print(f"Median strategy annualised return: {median_strategy_return:.2f}%")
        print(f"Median Buy & Hold annualised return: {median_buy_hold_return:.2f}%")
        print(f"Median strategy Sharpe: {median_strategy_sharpe:.2f}")
        print(f"Median Buy & Hold Sharpe: {median_buy_hold_sharpe:.2f}")
        print(f"Median strategy max drawdown: {median_strategy_dd:.2f}%")
        print(f"Median Buy & Hold max drawdown: {median_buy_hold_dd:.2f}%")
        print(f"Median market exposure: {median_market_exposure:.1f}%")

    original_eligible = [r for r in [evaluate_ticker_b007(ticker) for ticker in TICKERS] if r["eligible"]]
    combined_eligible = original_eligible + eligible_assets
    if combined_eligible:
        positive_returns = sum(1 for r in combined_eligible if r["strategy_total_return"] > 0)
        beat_bh = sum(1 for r in combined_eligible if r["strategy_total_return"] > r["buy_hold_total_return"])
        sharpe_beats = sum(1 for r in combined_eligible if r["strategy_sharpe"] > r["buy_hold_sharpe"])
        dd_smaller = sum(1 for r in combined_eligible if r["strategy_max_drawdown"] > r["buy_hold_max_drawdown"])
        median_strategy_return = np.median([r["strategy_annualised_return"] for r in combined_eligible]) * 100
        median_buy_hold_return = np.median([r["buy_hold_annualised_return"] for r in combined_eligible]) * 100
        median_strategy_sharpe = np.median([r["strategy_sharpe"] for r in combined_eligible])
        median_buy_hold_sharpe = np.median([r["buy_hold_sharpe"] for r in combined_eligible])
        median_strategy_dd = np.median([r["strategy_max_drawdown"] for r in combined_eligible]) * 100
        median_buy_hold_dd = np.median([r["buy_hold_max_drawdown"] for r in combined_eligible]) * 100
        median_market_exposure = np.median([r["market_exposure"] for r in combined_eligible])

        print("\nCombined summary: original 8 B007 assets + additional B008 eligible assets")
        print(f"Eligible assets: {len(combined_eligible)}")
        print(f"Positive-return strategy assets: {positive_returns} / {len(combined_eligible)}")
        print(f"Assets where strategy beats Buy & Hold: {beat_bh} / {len(combined_eligible)}")
        print(f"Assets where strategy Sharpe exceeds Buy & Hold: {sharpe_beats} / {len(combined_eligible)}")
        print(f"Assets where strategy max drawdown is smaller than Buy & Hold: {dd_smaller} / {len(combined_eligible)}")
        print(f"Median strategy annualised return: {median_strategy_return:.2f}%")
        print(f"Median Buy & Hold annualised return: {median_buy_hold_return:.2f}%")
        print(f"Median strategy Sharpe: {median_strategy_sharpe:.2f}")
        print(f"Median Buy & Hold Sharpe: {median_buy_hold_sharpe:.2f}")
        print(f"Median strategy max drawdown: {median_strategy_dd:.2f}%")
        print(f"Median Buy & Hold max drawdown: {median_buy_hold_dd:.2f}%")
        print(f"Median market exposure: {median_market_exposure:.1f}%")

    if ineligible_assets:
        print("\nIneligible additional assets:")
        for ticker, reason in ineligible_assets:
            print(f"  {ticker}: {reason}")

    print("\nFrozen Backtest 006 rules retained exactly:")
    print("Entry: previous-day SMA20 > SMA50, previous-day RSI(14) > 50, previous-day Close > SMA200")
    print("Exit: original Backtest 003 exit logic")
    print("Transaction costs and look-ahead protections preserved exactly")


if __name__ == "__main__":
    main()