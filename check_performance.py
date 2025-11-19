#!/usr/bin/env python3
"""Check actual performance of ESPO, WRLD, FEX since Nov 12"""

import yfinance as yf
from datetime import datetime, timedelta

# Stocks the user invested in
stocks = ['ESPO', 'WRLD', 'FEX']

# Signal date from daily_signals.csv
signal_date = '2025-11-12'

# Predictions from the model
predictions = {
    'ESPO': {'prob': 0.991, 'predicted_return': 21.1, 'entry_price': 115.44},
    'WRLD': {'prob': 0.965, 'predicted_return': 13.55, 'entry_price': 131.89},
    'FEX': {'prob': 0.981, 'predicted_return': 19.03, 'entry_price': 117.37}
}

print("=" * 80)
print("PERFORMANCE CHECK: ESPO, WRLD, FEX")
print(f"Signal Date: {signal_date}")
print(f"Today: {datetime.now().strftime('%Y-%m-%d')}")
print("=" * 80)

for symbol in stocks:
    print(f"\n{symbol}:")
    print("-" * 40)

    pred = predictions[symbol]
    print(f"Model Confidence: {pred['prob']*100:.1f}%")
    print(f"Predicted Return (10-day): +{pred['predicted_return']:.1f}%")
    print(f"Entry Price (Nov 12): ${pred['entry_price']:.2f}")

    try:
        # Fetch data from signal date to today
        ticker = yf.Ticker(symbol)
        df = ticker.history(start=signal_date, end=None)

        if len(df) == 0:
            print(f"ERROR: No data available for {symbol}")
            continue

        # Get entry price (close on Nov 12 or next available day)
        entry_close = df.iloc[0]['Close']

        # Get current/latest price
        current_price = df.iloc[-1]['Close']

        # Calculate actual return
        actual_return = (current_price - entry_close) / entry_close * 100

        # Get 10-day return if we have enough data
        if len(df) >= 10:
            day_10_price = df.iloc[9]['Close']
            return_10d = (day_10_price - entry_close) / entry_close * 100
            print(f"10-Day Return (Nov 25): {return_10d:+.2f}%")
            print(f"Price on Day 10: ${day_10_price:.2f}")
        else:
            print(f"Days since signal: {len(df)} (not enough for 10-day check)")

        print(f"\nCurrent Price: ${current_price:.2f}")
        print(f"Actual Return: {actual_return:+.2f}%")

        # Compare to prediction
        if actual_return >= 11.0:
            print("✓ HIT TARGET (>11%)")
        else:
            print("✗ MISSED TARGET (<11%)")

        # Show prediction error
        error = actual_return - pred['predicted_return']
        print(f"Prediction Error: {error:+.2f}% (actual vs predicted)")

    except Exception as e:
        print(f"ERROR fetching data: {e}")

print("\n" + "=" * 80)
print("\nSUMMARY:")
print("The model predicted 11%+ gains in 10 days with very high confidence (96-99%).")
print("Let's see if the predictions were accurate...")
