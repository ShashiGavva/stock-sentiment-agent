import pandas as pd
import numpy as np
import yfinance as yf
import pickle
import time
import random
from lightgbm import LGBMClassifier, LGBMRegressor
from datetime import datetime
from features import build_features
from symbols import get_all_us_tickers
from curl_cffi import requests as curl_requests


# =====================================================
# CONFIG
# =====================================================
CLF_PATH = "models/clf_lgbm_11.pkl"
REG_PATH = "models/reg_q90_11.pkl"
OUTPUT_PATH = "data/daily_signals.csv"

BATCH_SIZE = 100  # tickers per batch
PREDICTION_THRESHOLD = 0.6  # probability cutoff for "Buy" signal
REQUEST_DELAY = 0.2  # seconds between requests to avoid rate limiting
MAX_RETRIES = 3  # number of retries for failed requests


# =====================================================
# HELPERS
# =====================================================
def create_session():
    """Create a curl_cffi session with browser impersonation."""
    try:
        session = curl_requests.Session(impersonate='chrome')
        return session
    except Exception:
        return None


def fetch_data(symbol, period="3mo", interval="1d", session=None, retry_count=0):
    """Fetch OHLCV data for a given symbol with retry logic and better error handling."""
    try:
        # Add a random delay to avoid rate limiting
        delay = REQUEST_DELAY + random.uniform(0, 0.1)
        time.sleep(delay)

        # Use Ticker object with session if available
        if session:
            ticker = yf.Ticker(symbol, session=session)
        else:
            ticker = yf.Ticker(symbol)

        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            # Retry with exponential backoff if we got empty data
            if retry_count < MAX_RETRIES:
                backoff_delay = (2 ** retry_count) * REQUEST_DELAY
                time.sleep(backoff_delay)
                return fetch_data(symbol, period, interval, session, retry_count + 1)
            return None

        df = df.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        return df
    except Exception as e:
        # Retry on errors with exponential backoff
        if retry_count < MAX_RETRIES:
            backoff_delay = (2 ** retry_count) * REQUEST_DELAY
            time.sleep(backoff_delay)
            return fetch_data(symbol, period, interval, session, retry_count + 1)
        return None


# =====================================================
# MAIN
# =====================================================
def main():
    print("📦 Loading models...")
    with open(CLF_PATH, "rb") as f:
        clf_pack = pickle.load(f)
    with open(REG_PATH, "rb") as f:
        reg_pack = pickle.load(f)
    clf = clf_pack["model"]
    reg = reg_pack["model"]

    print("🔍 Fetching tickers...")
    try:
        tickers = get_all_us_tickers()
    except Exception as e:
        print(f"⚠️ Could not fetch tickers: {e}")
        tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD"]
    print(f"✅ Loaded {len(tickers)} tickers")

    # Create a session with browser impersonation
    print("🌐 Creating session with browser impersonation...")
    session = create_session()
    if session:
        print("✅ Session created successfully")
    else:
        print("⚠️ Could not create session, using default")

    all_signals = []
    failed_count = 0
    success_count = 0

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        print(f"\n📊 Processing batch {i//BATCH_SIZE + 1}: {len(batch)} tickers ({i+1}-{i+len(batch)})")

        for sym in batch:
            df = fetch_data(sym, session=session)
            if df is None:
                failed_count += 1
                continue

            success_count += 1

            feats = build_features(df)
            if feats is None or feats.empty:
                continue

            # drop non-numeric and target columns
            drop_cols = ["future_return_10d", "target_11pct", "date", "symbol"]
            X = (
                feats.drop(columns=drop_cols, errors="ignore")
                .select_dtypes(include=[np.number])
                .iloc[-1:]
            )

            try:
                proba = clf.predict_proba(X)[0, 1]
                pred_q90 = reg.predict(X)[0]
            except Exception as e:
                print(f"⚠️ Skipped {sym}: {e}")
                continue

            if proba >= PREDICTION_THRESHOLD:
                all_signals.append(
                    {
                        "symbol": sym,
                        "prob_11pct_up": round(proba, 3),
                        "predicted_return_q90": round(pred_q90 * 100, 2),
                        "latest_close": feats["close"].iloc[-1],
                        "date": datetime.today().strftime("%Y-%m-%d"),
                    }
                )

        if (i // BATCH_SIZE + 1) % 1 == 0:  # Progress update every batch
            print(f"✅ {len(all_signals)} signals | ✓ {success_count} successful | ✗ {failed_count} failed")

    print(f"\n📈 Final stats: {success_count} successful downloads, {failed_count} failed")

    if all_signals:
        df_out = pd.DataFrame(all_signals).sort_values(by="prob_11pct_up", ascending=False)
        df_out.to_csv(OUTPUT_PATH, index=False)
        print(f"\n💾 Saved {len(df_out)} signals to {OUTPUT_PATH}")
        print(df_out.head(10))
    else:
        print("⚠️ No signals generated today.")


if __name__ == "__main__":
    main()
