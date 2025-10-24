# symbols.py
# Pull all US-listed tickers with automatic fallbacks and CSV caching.

from __future__ import annotations
import io, os, time, json
import pandas as pd
import requests, certifi

SYMDIR = "https://ftp.nasdaqtrader.com/dynamic/SymDir/"
CACHE_PATH = "data/cache/all_us_tickers.csv"
CACHE_MAX_AGE_SECONDS = 24 * 3600  # refresh daily

def _ensure_dirs():
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)

def _save_cache(symbols: list[str]) -> None:
    pd.DataFrame({"Symbol": symbols}).to_csv(CACHE_PATH, index=False)

def _load_cache() -> list[str] | None:
    if not os.path.exists(CACHE_PATH):
        return None
    try:
        df = pd.read_csv(CACHE_PATH)
        return df["Symbol"].dropna().astype(str).tolist()
    except Exception:
        return None

def _try(url: str) -> str | None:
    try:
        r = requests.get(url, headers={"User-Agent": "StockSignalsBot"}, timeout=20, verify=certifi.where())
        r.raise_for_status()
        return r.text
    except Exception:
        return None

def _get_from_nasdaq_trader() -> pd.DataFrame | None:
    txt1 = _try(SYMDIR + "nasdaqlisted.txt")
    txt2 = _try(SYMDIR + "otherlisted.txt")
    if not txt1 or not txt2:
        return None

    nasdaq = pd.read_csv(io.StringIO(txt1), sep="|")
    other = pd.read_csv(io.StringIO(txt2), sep="|")

    frames = []
    for df in (nasdaq, other):
        if "Symbol" not in df.columns:
            continue
        cols = ["Symbol"]
        for extra in ["ETF", "Test Issue"]:
            if extra in df.columns:
                cols.append(extra)
        frames.append(df[cols])

    df = pd.concat(frames, ignore_index=True).dropna(subset=["Symbol"])
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    return df.drop_duplicates("Symbol")

def _get_from_json_mirror() -> pd.DataFrame | None:
    """Fallback: NASDAQ publishes JSON mirror for tickers."""
    url = "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed-symbols.json"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        data = json.loads(r.text)
        symbols = [d["Symbol"] for d in data if "Symbol" in d]
        return pd.DataFrame({"Symbol": symbols})
    except Exception:
        return None

def _get_from_yahoo_indexes() -> pd.DataFrame | None:
    """Fallback: Collect symbols from main US indexes via yfinance tickers lists."""
    import yfinance as yf
    tickers = set()
    for idx in ["^GSPC", "^IXIC", "^DJI"]:
        try:
            info = yf.Ticker(idx).constituents
            tickers.update(info.keys())
        except Exception:
            continue
    return pd.DataFrame({"Symbol": sorted(tickers)}) if tickers else None

def get_all_us_tickers(force_refresh: bool = False, include_etf: bool = False, min_len: int = 1) -> list[str]:
    _ensure_dirs()

    # Use cache if recent
    if not force_refresh and os.path.exists(CACHE_PATH):
        age = time.time() - os.path.getmtime(CACHE_PATH)
        if age < CACHE_MAX_AGE_SECONDS:
            cached = _load_cache()
            if cached:
                return cached

    df = _get_from_nasdaq_trader()
    if df is None:
        df = _get_from_json_mirror()
    if df is None:
        df = _get_from_yahoo_indexes()
    if df is None:
        cached = _load_cache()
        if cached:
            return cached
        raise RuntimeError("Unable to fetch any US ticker source.")

    if "Test Issue" in df.columns:
        df = df[df["Test Issue"].astype(str).str.upper() != "Y"]
    if not include_etf and "ETF" in df.columns:
        df = df[df["ETF"].astype(str).str.upper() != "Y"]

    df = df[df["Symbol"].str.len() >= min_len]
    df = df[["Symbol"]].drop_duplicates().sort_values("Symbol").reset_index(drop=True)
    symbols = df["Symbol"].tolist()
    _save_cache(symbols)
    return symbols
