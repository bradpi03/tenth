import yfinance as yf
import pandas as pd


STARTING_CAPITAL = 1000
TICKER = "AAPL"


def main():
    print("\nTENTH — BACKTEST 001")
    print(f"Ticker: {TICKER}")

    # Download enough history to test the idea properly
    data = yf.download(
        TICKER,
        period="5y",
        interval="1d",
        auto_adjust=True,
        progress=False,
    )

    # yfinance may return multi-level columns
    if isinstance(data.columns, pd.MultiIndex):
        close = data["Close"][TICKER]
    else:
        close = data["Close"]

    df = pd.DataFrame({"Close": close}).dropna()

    # Trend indicators
    df["SMA20"] = df["Close"].rolling(20).mean()
    df["SMA50"] = df["Close"].rolling(50).mean()

    # Simple hypothesis:
    # Own Apple when short-term trend is above longer-term trend.
    df["Signal"] = (df["SMA20"] > df["SMA50"]).astype(int)

    # Daily Apple return
    df["Market_Return"] = df["Close"].pct_change()

    # IMPORTANT:
    # Yesterday's signal determines today's position.
    # This avoids accidentally using future information.
    df["Strategy_Return"] = (
        df["Signal"].shift(1) * df["Market_Return"]
    )

    df = df.dropna()

    # Compound both approaches
    df["Buy_Hold_Value"] = (
        STARTING_CAPITAL * (1 + df["Market_Return"]).cumprod()
    )

    df["Strategy_Value"] = (
        STARTING_CAPITAL * (1 + df["Strategy_Return"]).cumprod()
    )

    buy_hold_final = df["Buy_Hold_Value"].iloc[-1]
    strategy_final = df["Strategy_Value"].iloc[-1]

    buy_hold_return = (
        (buy_hold_final / STARTING_CAPITAL) - 1
    ) * 100

    strategy_return = (
        (strategy_final / STARTING_CAPITAL) - 1
    ) * 100

    days_in_market = df["Signal"].sum()
    total_days = len(df)
    exposure = (days_in_market / total_days) * 100

    print(f"\nStarting capital: ${STARTING_CAPITAL:,.2f}")
    print(f"Trading days tested: {total_days}")

    print("\nBUY & HOLD")
    print(f"Final value: ${buy_hold_final:,.2f}")
    print(f"Return: {buy_hold_return:.2f}%")

    print("\nTENTH STRATEGY")
    print(f"Final value: ${strategy_final:,.2f}")
    print(f"Return: {strategy_return:.2f}%")
    print(f"Market exposure: {exposure:.1f}%")

    print("\nLatest signal:")
    print("BUY / HOLD" if df["Signal"].iloc[-1] == 1 else "OUT")

    print("\nLatest data:")
    print(
        df[
            ["Close", "SMA20", "SMA50", "Signal"]
        ].tail()
    )


if __name__ == "__main__":
    main()