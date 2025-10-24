import numpy as np
import pandas as pd
from typing import Tuple

def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    h, l, c = df['High'], df['Low'], df['Close']
    pc = c.shift(1)
    tr = pd.concat([h-l, (h-pc).abs(), (l-pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()

def rsi(series: pd.Series, n: int = 14) -> pd.Series:
    d = series.diff()
    up = d.clip(lower=0)
    dn = -d.clip(upper=0)
    rs = up.rolling(n).mean() / dn.rolling(n).mean().replace(0, np.nan)
    return (100 - 100/(1+rs)).fillna(50)

def macd(series: pd.Series, fast=12, slow=26, sig=9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    ef = series.ewm(span=fast, adjust=False).mean()
    es = series.ewm(span=slow, adjust=False).mean()
    line = ef - es
    signal = line.ewm(span=sig, adjust=False).mean()
    hist = line - signal
    return line, signal, hist

def add_tech_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['ATR14'] = atr(df, 14)
    df['RSI14'] = rsi(df['Close'], 14)
    m, s, h = macd(df['Close'], 12, 26, 9)
    df['MACD'], df['MACDsig'], df['MACDh'] = m, s, h
    df['Ret1'] = df['Close'].pct_change()
    df['Ret5'] = df['Close'].pct_change(5)
    for n in (10, 50, 200):
        df[f'SMA{n}'] = df['Close'].rolling(n).mean()
        df[f'SMA{n}_pct'] = (df['Close']/df[f'SMA{n}'] - 1)
    df['VolMA20'] = df['Volume'].rolling(20).mean()
    df['DollarVol'] = df['Close'] * df['Volume']
    return df

def future_max_return(close: pd.Series, h: int) -> pd.Series:
    fmax = close[::-1].rolling(h).max()[::-1].shift(-1)
    return (fmax/close) - 1
