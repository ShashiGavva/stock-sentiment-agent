"""
Intraday Features for Day Trading
Includes VWAP, RSI, MACD, Bollinger Bands, and other day trading indicators
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta


def fetch_intraday_data(symbol, interval="5m", days_back=5):
    """
    Fetch intraday price data for day trading.

    Args:
        symbol: Stock ticker
        interval: Time interval (1m, 2m, 5m, 15m, 30m, 60m, 90m)
        days_back: Number of days of historical data

    Returns:
        DataFrame with OHLCV data
    """
    try:
        # Calculate period
        if days_back <= 1:
            period = "1d"
        elif days_back <= 5:
            period = "5d"
        elif days_back <= 30:
            period = "1mo"
        else:
            period = "3mo"

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=30
        )

        if df.empty:
            return None

        # Handle MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]

        # Rename columns
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]

        # Rename Datetime to datetime if needed
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'timestamp'})
        elif 'date' in df.columns:
            df = df.rename(columns={'date': 'timestamp'})

        return df

    except Exception as e:
        print(f"Error fetching intraday data for {symbol}: {e}")
        return None


def calculate_vwap(df):
    """
    Calculate Volume Weighted Average Price (VWAP).

    VWAP = Σ(Price × Volume) / Σ(Volume)
    where Price = (High + Low + Close) / 3
    """
    df = df.copy()

    # Typical price (HL2 or HLC/3)
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3

    # Cumulative volume × typical price
    df['cumulative_tpv'] = (df['typical_price'] * df['volume']).cumsum()

    # Cumulative volume
    df['cumulative_volume'] = df['volume'].cumsum()

    # VWAP
    df['vwap'] = df['cumulative_tpv'] / df['cumulative_volume']

    # VWAP deviation
    df['vwap_deviation'] = ((df['close'] - df['vwap']) / df['vwap']) * 100

    # Distance from VWAP in percentage
    df['distance_from_vwap'] = df['vwap_deviation']

    return df


def calculate_rsi(df, period=14):
    """
    Calculate Relative Strength Index (RSI).

    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss
    """
    df = df.copy()

    # Calculate price changes
    delta = df['close'].diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    # Calculate average gain and loss
    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    df['rsi'] = 100 - (100 / (1 + rs))

    # RSI signals
    df['rsi_overbought'] = df['rsi'] > 70
    df['rsi_oversold'] = df['rsi'] < 30

    return df


def calculate_macd(df, fast=12, slow=26, signal=9):
    """
    Calculate MACD (Moving Average Convergence Divergence).

    MACD Line = 12-EMA - 26-EMA
    Signal Line = 9-EMA of MACD
    Histogram = MACD - Signal
    """
    df = df.copy()

    # Calculate EMAs
    ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
    ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

    # MACD line
    df['macd'] = ema_fast - ema_slow

    # Signal line
    df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()

    # Histogram
    df['macd_histogram'] = df['macd'] - df['macd_signal']

    # MACD crossover signals
    df['macd_bullish_cross'] = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
    df['macd_bearish_cross'] = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))

    return df


def calculate_bollinger_bands(df, period=20, std_dev=2):
    """
    Calculate Bollinger Bands.

    Middle Band = 20-SMA
    Upper Band = Middle + (2 × StdDev)
    Lower Band = Middle - (2 × StdDev)
    """
    df = df.copy()

    # Middle band (SMA)
    df['bb_middle'] = df['close'].rolling(window=period).mean()

    # Standard deviation
    std = df['close'].rolling(window=period).std()

    # Upper and lower bands
    df['bb_upper'] = df['bb_middle'] + (std_dev * std)
    df['bb_lower'] = df['bb_middle'] - (std_dev * std)

    # Band width
    df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100

    # %B indicator (position within bands)
    df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Bollinger squeeze (low volatility)
    df['bb_squeeze'] = df['bb_width'] < df['bb_width'].rolling(window=50).mean()

    return df


def calculate_volume_indicators(df):
    """
    Calculate volume-based indicators.
    """
    df = df.copy()

    # Volume moving average
    df['volume_ma'] = df['volume'].rolling(window=20).mean()

    # Relative volume
    df['relative_volume'] = df['volume'] / df['volume_ma']

    # Volume spike (2x average)
    df['volume_spike'] = df['relative_volume'] > 2.0

    # On-Balance Volume (OBV)
    df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

    return df


def calculate_support_resistance(df, window=20):
    """
    Calculate support and resistance levels based on swing highs/lows.
    """
    df = df.copy()

    # Swing highs (resistance)
    df['swing_high'] = df['high'].rolling(window=window, center=True).max()
    df['is_resistance'] = df['high'] == df['swing_high']

    # Swing lows (support)
    df['swing_low'] = df['low'].rolling(window=window, center=True).min()
    df['is_support'] = df['low'] == df['swing_low']

    # Recent resistance/support levels
    df['resistance'] = df[df['is_resistance']]['high'].iloc[-1] if any(df['is_resistance']) else df['high'].max()
    df['support'] = df[df['is_support']]['low'].iloc[-1] if any(df['is_support']) else df['low'].min()

    return df


def calculate_momentum_indicators(df):
    """
    Calculate momentum indicators.
    """
    df = df.copy()

    # Rate of Change (ROC)
    df['roc'] = ((df['close'] - df['close'].shift(10)) / df['close'].shift(10)) * 100

    # Stochastic Oscillator
    low_min = df['low'].rolling(window=14).min()
    high_max = df['high'].rolling(window=14).max()
    df['stoch_k'] = ((df['close'] - low_min) / (high_max - low_min)) * 100
    df['stoch_d'] = df['stoch_k'].rolling(window=3).mean()

    # Money Flow Index (MFI)
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    money_flow = typical_price * df['volume']

    positive_flow = money_flow.where(typical_price > typical_price.shift(1), 0).rolling(window=14).sum()
    negative_flow = money_flow.where(typical_price < typical_price.shift(1), 0).rolling(window=14).sum()

    mfi_ratio = positive_flow / negative_flow
    df['mfi'] = 100 - (100 / (1 + mfi_ratio))

    return df


def build_intraday_features(symbol, interval="5m", days_back=5):
    """
    Build complete feature set for day trading.

    Args:
        symbol: Stock ticker
        interval: Time interval (1m, 5m, 15m, etc.)
        days_back: Days of historical data

    Returns:
        DataFrame with all intraday features
    """
    # Fetch intraday data
    df = fetch_intraday_data(symbol, interval=interval, days_back=days_back)

    if df is None or df.empty:
        return None

    # Calculate all indicators
    df = calculate_vwap(df)
    df = calculate_rsi(df)
    df = calculate_macd(df)
    df = calculate_bollinger_bands(df)
    df = calculate_volume_indicators(df)
    df = calculate_support_resistance(df)
    df = calculate_momentum_indicators(df)

    return df


def generate_day_trading_signals(df):
    """
    Generate day trading signals based on technical indicators.

    Returns:
        List of signal dictionaries
    """
    if df is None or df.empty or len(df) < 2:
        return []

    signals = []
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # 1. VWAP Crossover Signals
    if prev['close'] < prev['vwap'] and latest['close'] > latest['vwap']:
        signals.append({
            'type': 'BUY',
            'indicator': 'VWAP Crossover',
            'reason': f"Price crossed above VWAP (${latest['vwap']:.2f})",
            'strength': 'Medium',
            'price': latest['close']
        })
    elif prev['close'] > prev['vwap'] and latest['close'] < latest['vwap']:
        signals.append({
            'type': 'SELL',
            'indicator': 'VWAP Crossover',
            'reason': f"Price crossed below VWAP (${latest['vwap']:.2f})",
            'strength': 'Medium',
            'price': latest['close']
        })

    # 2. RSI Signals
    if latest['rsi_oversold'] and latest['rsi'] > prev['rsi']:
        signals.append({
            'type': 'BUY',
            'indicator': 'RSI',
            'reason': f"RSI oversold and turning up ({latest['rsi']:.1f})",
            'strength': 'High',
            'price': latest['close']
        })
    elif latest['rsi_overbought'] and latest['rsi'] < prev['rsi']:
        signals.append({
            'type': 'SELL',
            'indicator': 'RSI',
            'reason': f"RSI overbought and turning down ({latest['rsi']:.1f})",
            'strength': 'High',
            'price': latest['close']
        })

    # 3. MACD Signals
    if latest['macd_bullish_cross']:
        signals.append({
            'type': 'BUY',
            'indicator': 'MACD',
            'reason': 'MACD bullish crossover',
            'strength': 'High',
            'price': latest['close']
        })
    elif latest['macd_bearish_cross']:
        signals.append({
            'type': 'SELL',
            'indicator': 'MACD',
            'reason': 'MACD bearish crossover',
            'strength': 'High',
            'price': latest['close']
        })

    # 4. Bollinger Band Signals
    if latest['close'] < latest['bb_lower'] and latest['rsi'] < 40:
        signals.append({
            'type': 'BUY',
            'indicator': 'Bollinger Bands',
            'reason': f"Price below lower band with low RSI",
            'strength': 'Medium',
            'price': latest['close']
        })
    elif latest['close'] > latest['bb_upper'] and latest['rsi'] > 60:
        signals.append({
            'type': 'SELL',
            'indicator': 'Bollinger Bands',
            'reason': f"Price above upper band with high RSI",
            'strength': 'Medium',
            'price': latest['close']
        })

    # 5. Volume Spike Signals
    if latest['volume_spike'] and latest['close'] > prev['close']:
        signals.append({
            'type': 'BUY',
            'indicator': 'Volume',
            'reason': f"Volume spike on upward price movement ({latest['relative_volume']:.1f}x avg)",
            'strength': 'Medium',
            'price': latest['close']
        })

    return signals


def get_market_status():
    """
    Determine if market is open, pre-market, or after-hours.

    Returns:
        dict with market status info
    """
    now = datetime.now()

    # Market hours (Eastern Time - adjust for your timezone)
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    premarket_start = now.replace(hour=4, minute=0, second=0, microsecond=0)
    afterhours_end = now.replace(hour=20, minute=0, second=0, microsecond=0)

    # Check if weekend
    if now.weekday() >= 5:  # Saturday or Sunday
        return {
            'status': 'CLOSED',
            'message': 'Market is closed (Weekend)',
            'next_open': 'Monday 9:30 AM ET'
        }

    # Check market hours
    if premarket_start <= now < market_open:
        return {
            'status': 'PRE_MARKET',
            'message': 'Pre-market trading',
            'next_open': f"Market opens at 9:30 AM ET"
        }
    elif market_open <= now < market_close:
        return {
            'status': 'OPEN',
            'message': 'Market is open',
            'time_to_close': str(market_close - now).split('.')[0]
        }
    elif market_close <= now < afterhours_end:
        return {
            'status': 'AFTER_HOURS',
            'message': 'After-hours trading',
            'next_open': 'Tomorrow 9:30 AM ET'
        }
    else:
        return {
            'status': 'CLOSED',
            'message': 'Market is closed',
            'next_open': 'Tomorrow 9:30 AM ET'
        }


if __name__ == "__main__":
    # Test the module
    symbol = "AAPL"
    print(f"Fetching intraday data for {symbol}...")

    df = build_intraday_features(symbol, interval="5m", days_back=1)

    if df is not None:
        print(f"\n✅ Fetched {len(df)} data points")
        print(f"\nLatest data:")
        print(df[['timestamp', 'close', 'vwap', 'rsi', 'macd', 'volume']].tail())

        print(f"\n📊 Generating signals...")
        signals = generate_day_trading_signals(df)

        if signals:
            print(f"\n🎯 Found {len(signals)} signals:")
            for sig in signals:
                print(f"  {sig['type']:4} | {sig['indicator']:15} | {sig['reason']}")
        else:
            print("No signals at this time")
    else:
        print("Failed to fetch data")

    # Market status
    market = get_market_status()
    print(f"\n📈 Market Status: {market['status']} - {market['message']}")
