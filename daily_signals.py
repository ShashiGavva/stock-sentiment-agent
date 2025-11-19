import pandas as pd
import numpy as np
import yfinance as yf
import pickle
from lightgbm import LGBMClassifier, LGBMRegressor
from datetime import datetime
from features import build_features
from symbols import get_all_us_tickers
from utils import is_valid_stock


# =====================================================
# CONFIG
# =====================================================
import config

CLF_PATH = config.CLF_PATH  # Now points to clf_lgbm_08.pkl (8% target)
REG_PATH = config.Q90_PATH  # Now points to reg_q90_08.pkl
OUTPUT_PATH = "data/daily_signals.csv"

BATCH_SIZE = 500  # tickers per batch
PREDICTION_THRESHOLD = config.CONFIDENCE_TIERS['medium']  # 0.6 - medium confidence threshold
MIN_VOLUME = 100000  # minimum average daily volume (liquidity filter)


# =====================================================
# HELPERS
# =====================================================
def fetch_data(symbol, period="3mo", interval="1d"):
    """Fetch OHLCV data for a given symbol."""
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

    all_signals = []
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i : i + BATCH_SIZE]
        print(f"\n📊 Processing batch {i//BATCH_SIZE + 1}: {len(batch)} tickers ({i+1}-{i+len(batch)})")

        for sym in batch:
            df = fetch_data(sym)
            if df is None:
                continue

            feats = build_features(df, symbol=sym, include_sentiment=True)
            if feats is None or feats.empty:
                continue

            # Validate that this is a tradeable stock (not ETF, mutual fund, etc.)
            validation = is_valid_stock(sym, min_volume=MIN_VOLUME)
            if not validation['is_valid']:
                continue  # Skip ETFs, mutual funds, low-volume stocks, etc.

            # drop non-numeric and target columns
            drop_cols = ["future_return_10d", "target_hit", "date", "symbol"]
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

        print(f"✅ {len(all_signals)} potential BUY signals so far...")

    if all_signals:
        df_out = pd.DataFrame(all_signals).sort_values(by="prob_11pct_up", ascending=False)
        df_out.to_csv(OUTPUT_PATH, index=False)
        print(f"\n💾 Saved {len(df_out)} signals to {OUTPUT_PATH}")
        print(df_out.head(10))
    else:
        print("⚠️ No signals generated today.")


if __name__ == "__main__":
    main()
