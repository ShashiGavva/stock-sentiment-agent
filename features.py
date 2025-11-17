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
        # Ensure numeric columns
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

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


def calculate_risk_indicators(df):
    """
    Calculate additional risk indicators for confidence adjustment.
    These are NOT used for model training, but for risk assessment.
    """
    try:
        indicators = {}

        # Ensure we have data
        if df is None or df.empty or len(df) < 10:
            return None

        latest = df.iloc[-1]

        # 52-week high/low calculations
        window_1y = min(252, len(df))
        high_52w = df["high"].tail(window_1y).max()
        low_52w = df["low"].tail(window_1y).min()
        current_close = latest["close"]

        indicators['pct_from_high'] = ((current_close - high_52w) / high_52w) * 100
        indicators['pct_from_low'] = ((current_close - low_52w) / low_52w) * 100

        # Moving average positions
        indicators['below_ma50'] = current_close < latest.get("SMA50", current_close)
        indicators['below_ma200'] = False  # We don't have MA200 yet

        # MA alignment (bullish if MA10 > MA20 > MA50)
        ma10 = latest.get("SMA10", 0)
        ma20 = latest.get("SMA20", 0)
        ma50 = latest.get("SMA50", 0)
        indicators['ma_alignment_bullish'] = (ma10 > ma20) and (ma20 > ma50)

        # Volume trend (last 5 days vs prior 5 days)
        if len(df) >= 10:
            recent_vol = df["volume"].tail(5).mean()
            prior_vol = df["volume"].tail(10).head(5).mean()
            if prior_vol > 0:
                indicators['volume_trend'] = (recent_vol - prior_vol) / prior_vol
            else:
                indicators['volume_trend'] = 0
        else:
            indicators['volume_trend'] = 0

        # Volatility ratio (current vs average)
        current_vol = latest.get("volatility_20", 0.02)
        avg_vol = df["volatility_20"].mean()
        if avg_vol > 0:
            indicators['volatility_ratio'] = current_vol / avg_vol
        else:
            indicators['volatility_ratio'] = 1.0

        # Recent 1-week return
        if len(df) >= 5:
            week_ago_close = df["close"].iloc[-5]
            indicators['recent_1w_return'] = ((current_close - week_ago_close) / week_ago_close) * 100
        else:
            indicators['recent_1w_return'] = 0

        # Price trend (positive if rising)
        if len(df) >= 10:
            indicators['price_trend'] = (df["close"].tail(10).pct_change().mean())
        else:
            indicators['price_trend'] = 0

        # Relative strength (vs itself - momentum)
        if len(df) >= 20:
            indicators['relative_strength'] = (current_close / df["close"].iloc[-20] - 1)
        else:
            indicators['relative_strength'] = 0

        # RSI approximation (simple version)
        if len(df) >= 14:
            delta = df["close"].diff()
            gain = (delta.where(delta > 0, 0)).tail(14).mean()
            loss = (-delta.where(delta < 0, 0)).tail(14).mean()
            if loss != 0:
                rs = gain / loss
                indicators['rsi'] = 100 - (100 / (1 + rs))
            else:
                indicators['rsi'] = 100 if gain > 0 else 50
        else:
            indicators['rsi'] = 50

        return indicators

    except Exception as e:
        print(f"Risk indicator error: {e}")
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
