import os
import time
import pickle
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from lightgbm import LGBMClassifier, LGBMRegressor
from features import build_features
from symbols import get_all_us_tickers
import config

# =====================================================
# CONFIG
# =====================================================
DATA_DIR = config.DATA_DIR
MODEL_DIR = config.MODELS_DIR
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)

# Update model names to reflect new 8% target
CLF_PATH = os.path.join(MODEL_DIR, "clf_lgbm_08.pkl")
REG_PATH = os.path.join(MODEL_DIR, "reg_q90_08.pkl")
DATA_PATH = os.path.join(DATA_DIR, "training_dataset_full.csv")
TICKER_CACHE = os.path.join(DATA_DIR, "us_tickers.csv")

BATCH_SIZE = 500
TARGET_RETURN = config.TARGET_UPSIDE  # Now 0.08 (8%) instead of 0.11 (11%)
FUTURE_DAYS = config.HORIZON_DAYS

# Auto-refresh thresholds
MODEL_MAX_AGE_DAYS = 30
CACHE_MAX_AGE_DAYS = 30


# =====================================================
# HELPERS
# =====================================================
def is_stale(filepath: str, max_age_days: int) -> bool:
    """Check if a file is older than max_age_days."""
    if not os.path.exists(filepath):
        return True
    mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
    age = (datetime.now() - mtime).days
    return age > max_age_days


def fetch_data(symbol, period="6mo", interval="1d"):
    """Fetch price data for a single ticker."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        return df
    except Exception as e:
        print(f"⚠️ {symbol}: {e}")
        return None


def build_dataset(tickers):
    """Build feature dataset across tickers."""
    frames = []
    for sym in tickers:
        df = fetch_data(sym)
        if df is None:
            continue
        feats = build_features(df)
        if feats is None or feats.empty:
            continue
        feats["symbol"] = sym
        frames.append(feats)
    if not frames:
        raise RuntimeError("No data built — check connectivity or symbols.")
    return pd.concat(frames, ignore_index=True)


# =====================================================
# MAIN TRAINING LOGIC
# =====================================================
def train():
    # --- Check ticker freshness
    if is_stale(TICKER_CACHE, CACHE_MAX_AGE_DAYS):
        print("🔁 Ticker cache stale — refreshing...")
        tickers = get_all_us_tickers(force_refresh=True)
    else:
        tickers = get_all_us_tickers()

    print(f"✅ Loaded {len(tickers)} tickers for training")

    # --- Check model freshness
    retrain_needed = (
        is_stale(CLF_PATH, MODEL_MAX_AGE_DAYS)
        or is_stale(REG_PATH, MODEL_MAX_AGE_DAYS)
        or not os.path.exists(DATA_PATH)
    )

    if not retrain_needed:
        print("✅ Models are fresh — skipping retraining.")
        return

    # --- Build dataset in batches
    print("📦 Building dataset...")
    all_frames = []
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        print(f"📊 Processing batch {i//BATCH_SIZE + 1}: {len(batch)} tickers ({i+1}-{i+len(batch)})")
        try:
            data = build_dataset(batch)
            all_frames.append(data)
            partial = os.path.join(DATA_DIR, f"batch_{i//BATCH_SIZE + 1}_raw.csv")
            data.to_csv(partial, index=False)
            print(f"💾 Saved partial data to {partial}")
        except Exception as e:
            print(f"⚠️ Error in batch {i//BATCH_SIZE + 1}: {e}")

    df = pd.concat(all_frames, ignore_index=True)
    print(f"✅ Final dataset size: {df.shape[0]} rows × {df.shape[1]} columns")

    # --- Define target (using config TARGET_UPSIDE)
    df["target_hit"] = (df["future_return_10d"] >= TARGET_RETURN).astype(int)
    X = df.drop(columns=["future_return_10d", "target_hit", "date", "symbol"], errors="ignore")
    y = df["target_hit"]

    # --- Train classifier
    print(f"🚀 Training LightGBM classifier (target ≥{TARGET_RETURN*100:.0f}%)...")
    clf = LGBMClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
    )
    clf.fit(X, y)
    print("✅ Classifier trained")

    # --- Train regressor
    print("🚀 Training LightGBM regression model (quantile q=0.90)...")
    reg = LGBMRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        objective="quantile",
        alpha=0.9,
        random_state=42,
    )
    reg.fit(X, df["future_return_10d"])
    print("✅ Regression model trained")

    # --- Save artifacts
    with open(CLF_PATH, "wb") as f:
        pickle.dump({"model": clf, "features": X.columns.tolist()}, f)
    with open(REG_PATH, "wb") as f:
        pickle.dump({"model": reg, "features": X.columns.tolist()}, f)
    df.to_csv(DATA_PATH, index=False)

    print("\n🎯 Models saved in 'models/'")
    print(f"   - Classifier: {CLF_PATH}")
    print(f"   - Regressor:  {REG_PATH}")
    print(f"💾 Full training dataset saved to {DATA_PATH}")


if __name__ == "__main__":
    train()
