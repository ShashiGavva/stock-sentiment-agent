#!/usr/bin/env python3
"""Investigate the ticker symbols that were recommended"""

import yfinance as yf

tickers = ['ESPO', 'WRLD', 'FEX']

print("=" * 80)
print("INVESTIGATING TICKER SYMBOLS")
print("=" * 80)

for symbol in tickers:
    print(f"\n{symbol}:")
    print("-" * 40)

    try:
        ticker = yf.Ticker(symbol)

        # Try to get info
        info = ticker.info

        if info:
            print(f"Name: {info.get('longName', 'N/A')}")
            print(f"Exchange: {info.get('exchange', 'N/A')}")
            print(f"Quote Type: {info.get('quoteType', 'N/A')}")
            print(f"Market: {info.get('market', 'N/A')}")

            # Check if it's an ETF
            if info.get('quoteType') == 'ETF':
                print("⚠️ This is an ETF, not a stock!")

        else:
            print("ERROR: No info available")

        # Try to get recent history
        hist = ticker.history(period="1mo")
        if not hist.empty:
            latest = hist.iloc[-1]
            print(f"Latest close: ${latest['Close']:.2f}")
            print(f"Latest date: {hist.index[-1].strftime('%Y-%m-%d')}")
        else:
            print("ERROR: No price history available")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 80)
print("\nCHECKING IF THESE ARE ETFs OR FUNDS...")
print("=" * 80)

# These are likely ETFs
etf_mapping = {
    'ESPO': 'VanEck Video Gaming and eSports ETF',
    'WRLD': 'Assumes World ETF or similar',
    'FEX': 'Unknown - possibly delisted'
}

for symbol, desc in etf_mapping.items():
    print(f"{symbol}: {desc}")
