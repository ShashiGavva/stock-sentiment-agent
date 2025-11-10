import pandas as pd
import numpy as np
import yfinance as yf

# =====================================================
# Build stock feature set for model training
# =====================================================

def get_stock_data(symbol, period="6mo", interval="1d"):
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            print(f"skip {symbol} — no data")
            return None
        # flatten possible multi-index columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.reset_index()
        df = df.rename(columns={
            "Date": "date",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume"
        })
        return df
    except Exception as e:
        print(f"skip {symbol} — {e}")
        return None


def build_features(df):
    """Safely compute technical indicators and target variables."""
    try:
        # Ensure close column is a Series
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

        # Moving averages
        df["SMA10"] = df["close"].rolling(window=10, min_periods=1).mean()
        df["SMA20"] = df["close"].rolling(window=20, min_periods=1).mean()
        df["SMA50"] = df["close"].rolling(window=50, min_periods=1).mean()

        # SMA percentage change
        df["SMA10_pct"] = df["SMA10"].pct_change().fillna(0)
        df["SMA20_pct"] = df["SMA20"].pct_change().fillna(0)
        df["SMA50_pct"] = df["SMA50"].pct_change().fillna(0)

        # Returns
        df["daily_return"] = df["close"].pct_change().fillna(0)

        # Price distance from SMAs
        df["price_vs_SMA10"] = (df["close"] - df["SMA10"]) / df["SMA10"]
        df["price_vs_SMA20"] = (df["close"] - df["SMA20"]) / df["SMA20"]
        df["price_vs_SMA50"] = (df["close"] - df["SMA50"]) / df["SMA50"]

        # Volatility
        df["volatility_10"] = df["daily_return"].rolling(10, min_periods=1).std().fillna(0)
        df["volatility_20"] = df["daily_return"].rolling(20, min_periods=1).std().fillna(0)

        # Lag features
        for lag in [1, 2, 3, 5]:
            df[f"return_lag_{lag}"] = df["daily_return"].shift(lag).fillna(0)

        # Future returns and targets
        df["future_return_10d"] = df["close"].shift(-10) / df["close"] - 1
        df["target_11pct"] = (df["future_return_10d"] >= 0.11).astype(int)

        df = df.dropna().reset_index(drop=True)
        return df

    except Exception as e:
        print(f"Feature build error: {e}")
        return None


def build_dataset(symbols, period="6mo", interval="1d"):
    """Combine multiple stocks into a single training DataFrame."""
    frames = []
    for sym in symbols:
        df = get_stock_data(sym, period=period, interval=interval)
        if df is None:
            continue
        feats = build_features(df)
        if feats is not None and not feats.empty:
            feats["symbol"] = sym
            frames.append(feats)
        else:
            print(f"skip {sym} — no features built")

    if not frames:
        raise RuntimeError("No data built — check connectivity or symbols.py")

    all_data = pd.concat(frames, ignore_index=True)
    return all_data


if __name__ == "__main__":
    test_symbols = ["AAPL", "MSFT", "NVDA"]
    data = build_dataset(test_symbols)
    print(data.tail())
