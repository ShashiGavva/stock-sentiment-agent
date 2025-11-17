import pandas as pd
import numpy as np
import yfinance as yf
import pickle
import time
import random
import warnings
from lightgbm import LGBMClassifier, LGBMRegressor
from datetime import datetime
from features import build_features, calculate_risk_indicators
from symbols import get_all_us_tickers
from curl_cffi import requests as curl_requests
from risk_adjustment import get_final_signal_assessment

# Suppress yfinance warnings and errors
warnings.filterwarnings('ignore')
import logging
logging.getLogger('yfinance').setLevel(logging.CRITICAL)


# =====================================================
# CONFIG
# =====================================================
CLF_PATH = "models/clf_lgbm_11.pkl"
REG_PATH = "models/reg_q90_11.pkl"
OUTPUT_PATH = "data/daily_signals.csv"

BATCH_SIZE = 100  # tickers per batch
PREDICTION_THRESHOLD = 0.6  # probability cutoff for "Buy" signal (applied to ADJUSTED confidence if USE_RISK_ADJUSTMENT=True)
REQUEST_DELAY = 0.15  # seconds between requests to avoid rate limiting
MAX_RETRIES = 2  # number of retries for failed requests
MIN_TICKER_LENGTH = 1  # minimum length for valid ticker symbols
MAX_TICKER_LENGTH = 5  # maximum length for valid ticker symbols (filters out warrants/complex instruments)

# Risk-Aware Confidence System
USE_RISK_ADJUSTMENT = True  # Enable risk-adjusted confidence scoring
MIN_SETUP_QUALITY = 30  # Minimum setup quality score (0-100) to include signal


# =====================================================
# HELPERS
# =====================================================
def filter_tickers(tickers):
    """Filter ticker list to include only likely valid stock symbols."""
    filtered = []
    for ticker in tickers:
        # Skip tickers with invalid characters or lengths
        if not ticker or len(ticker) < MIN_TICKER_LENGTH or len(ticker) > MAX_TICKER_LENGTH:
            continue
        # Skip warrants, rights, and other complex instruments
        if any(suffix in ticker for suffix in ['W', 'R', 'U', 'WS']):
            if len(ticker) > 4:  # Allow single letter tickers like 'W' but not 'AAPLW'
                continue
        # Skip preferred shares
        if '-' in ticker or '.' in ticker:
            continue
        filtered.append(ticker)
    return filtered


def create_session():
    """Create a curl_cffi session with browser impersonation."""
    try:
        session = curl_requests.Session(impersonate='chrome')
        return session
    except Exception:
        return None


def fetch_data(symbol, period="3mo", interval="1d", session=None, retry_count=0):
    """Fetch OHLCV data for a given symbol with smart retry logic."""
    try:
        # Add a random delay to avoid rate limiting
        if retry_count == 0:
            delay = REQUEST_DELAY + random.uniform(0, 0.1)
            time.sleep(delay)

        # Use Ticker object with session if available
        if session:
            ticker = yf.Ticker(symbol, session=session)
        else:
            ticker = yf.Ticker(symbol)

        df = ticker.history(period=period, interval=interval, auto_adjust=True)

        if df.empty:
            # Don't retry if the ticker is likely delisted or invalid
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

        # Keep only the columns we need (yfinance sometimes adds Dividends, Stock Splits, etc.)
        required_cols = ["date", "open", "high", "low", "close", "volume"]
        df = df[[col for col in required_cols if col in df.columns]]

        return df
    except Exception as e:
        error_msg = str(e).lower()
        # Only retry on network/rate-limit errors, not on delisted/invalid tickers
        should_retry = (
            'timeout' in error_msg or
            'connection' in error_msg or
            '429' in error_msg or
            'rate limit' in error_msg
        )

        if should_retry and retry_count < MAX_RETRIES:
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
        all_tickers = get_all_us_tickers()
    except Exception as e:
        print(f"⚠️ Could not fetch tickers: {e}")
        all_tickers = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD"]

    # Filter tickers to remove likely invalid ones
    print(f"📋 Filtering {len(all_tickers)} tickers...")
    tickers = filter_tickers(all_tickers)
    print(f"✅ Processing {len(tickers)} tickers (filtered out {len(all_tickers) - len(tickers)} invalid/complex symbols)")

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

    total_batches = (len(tickers) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1
        progress_pct = (i / len(tickers)) * 100
        print(f"\n📊 Batch {batch_num}/{total_batches} ({progress_pct:.1f}%): Processing {len(batch)} tickers")

        for sym in batch:
            df = fetch_data(sym, session=session)
            if df is None:
                failed_count += 1
                continue

            success_count += 1

            feats = build_features(df)
            if feats is None or feats.empty:
                continue

            # drop non-numeric and target columns, then select only the features the model was trained on
            drop_cols = ["future_return_10d", "target_11pct", "date", "symbol"]
            feature_names = clf_pack.get("features", [
                "close", "high", "low", "open", "volume",
                "SMA10", "SMA20", "SMA50",
                "SMA10_pct", "SMA20_pct", "SMA50_pct",
                "daily_return",
                "price_vs_SMA10", "price_vs_SMA20", "price_vs_SMA50",
                "volatility_10", "volatility_20",
                "return_lag_1", "return_lag_2", "return_lag_3", "return_lag_5"
            ])

            # Select only the features that the model was trained on, in the same order
            try:
                X = feats[feature_names].iloc[-1:]
            except KeyError as e:
                print(f"⚠️ Skipped {sym}: Missing required features: {e}")
                continue

            try:
                base_proba = clf.predict_proba(X)[0, 1]
                pred_q90 = reg.predict(X)[0]
            except Exception as e:
                print(f"⚠️ Skipped {sym}: {e}")
                continue

            # Apply risk-aware confidence adjustment
            if USE_RISK_ADJUSTMENT:
                # Calculate risk indicators from raw price data
                risk_indicators = calculate_risk_indicators(df)

                if risk_indicators is not None:
                    # Get full risk assessment
                    assessment = get_final_signal_assessment(base_proba, risk_indicators)

                    adjusted_proba = assessment['adjusted_probability']
                    setup_quality = assessment['setup_quality_score']
                    confidence_category = assessment['confidence_category']
                    position_size = assessment['position_size']

                    # Filter by adjusted confidence and setup quality
                    if adjusted_proba >= PREDICTION_THRESHOLD and setup_quality >= MIN_SETUP_QUALITY:
                        all_signals.append({
                            "symbol": sym,
                            "base_prob": round(base_proba, 3),
                            "adjusted_prob": round(adjusted_proba, 3),
                            "adjustment": round(assessment['adjustment_factor'], 2),
                            "setup_quality": setup_quality,
                            "confidence_category": confidence_category,
                            "position_size": position_size,
                            "predicted_return_q90": round(pred_q90 * 100, 2),
                            "latest_close": feats["close"].iloc[-1],
                            "risk_factors": "|".join(assessment['risk_factors']) if assessment['risk_factors'] else "none",
                            "failure_patterns": "|".join(assessment['failure_patterns']) if assessment['failure_patterns'] else "none",
                            "date": datetime.today().strftime("%Y-%m-%d"),
                        })
                else:
                    # Fall back to base probability if risk indicators can't be calculated
                    if base_proba >= PREDICTION_THRESHOLD:
                        all_signals.append({
                            "symbol": sym,
                            "base_prob": round(base_proba, 3),
                            "adjusted_prob": round(base_proba, 3),
                            "adjustment": 1.0,
                            "setup_quality": 50,  # Neutral
                            "confidence_category": "MODERATE_CONFIDENCE",
                            "position_size": 0.5,
                            "predicted_return_q90": round(pred_q90 * 100, 2),
                            "latest_close": feats["close"].iloc[-1],
                            "risk_factors": "insufficient_data",
                            "failure_patterns": "none",
                            "date": datetime.today().strftime("%Y-%m-%d"),
                        })
            else:
                # Original behavior without risk adjustment
                if base_proba >= PREDICTION_THRESHOLD:
                    all_signals.append({
                        "symbol": sym,
                        "prob_11pct_up": round(base_proba, 3),
                        "predicted_return_q90": round(pred_q90 * 100, 2),
                        "latest_close": feats["close"].iloc[-1],
                        "date": datetime.today().strftime("%Y-%m-%d"),
                    })

        if (i // BATCH_SIZE + 1) % 1 == 0:  # Progress update every batch
            print(f"✅ {len(all_signals)} signals | ✓ {success_count} successful | ✗ {failed_count} failed")

    print(f"\n📈 Final stats: {success_count} successful downloads, {failed_count} failed")

    if all_signals:
        df_out = pd.DataFrame(all_signals)

        # Sort by appropriate column depending on risk adjustment mode
        if USE_RISK_ADJUSTMENT and 'adjusted_prob' in df_out.columns:
            df_out = df_out.sort_values(by="adjusted_prob", ascending=False)
        elif 'prob_11pct_up' in df_out.columns:
            df_out = df_out.sort_values(by="prob_11pct_up", ascending=False)

        df_out.to_csv(OUTPUT_PATH, index=False)
        print(f"\n💾 Saved {len(df_out)} signals to {OUTPUT_PATH}")

        # Display results with appropriate formatting
        if USE_RISK_ADJUSTMENT and 'adjusted_prob' in df_out.columns:
            print("\n🎯 Top 10 Risk-Adjusted Signals:")
            print("=" * 120)
            display_cols = ['symbol', 'adjusted_prob', 'base_prob', 'setup_quality',
                           'confidence_category', 'position_size', 'predicted_return_q90',
                           'latest_close', 'risk_factors']
            print(df_out[display_cols].head(10).to_string(index=False))

            # Show distribution of confidence categories
            print("\n📊 Confidence Distribution:")
            if 'confidence_category' in df_out.columns:
                cat_dist = df_out['confidence_category'].value_counts()
                for cat, count in cat_dist.items():
                    print(f"  {cat}: {count} signals")
        else:
            print(df_out.head(10))
    else:
        print("⚠️ No signals generated today.")


if __name__ == "__main__":
    main()
