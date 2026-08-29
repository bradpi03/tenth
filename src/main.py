import yfinance as yf


def main():
    ticker = "AAPL"

    data = yf.download(
        ticker,
        period="1y",
        interval="1d",
        auto_adjust=True,
    )

    print("\nTENTH — MARKET DATA TEST")
    print(f"Ticker: {ticker}")
    print(f"Rows downloaded: {len(data)}")

    print("\nLatest data:")
    print(data.tail())


if __name__ == "__main__":
    main()
