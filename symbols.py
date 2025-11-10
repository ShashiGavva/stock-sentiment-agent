import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# =====================================================
# CONFIG
# =====================================================
CACHE_FILE = "data/us_tickers.csv"
CACHE_MAX_AGE_DAYS = 30

DATA_SOURCES = {
    "NASDAQ": "https://datahub.io/core/nasdaq-listings/r/nasdaq-listed.csv",
    "NYSE": "https://raw.githubusercontent.com/datasets/nyse-listed/master/data/nyse-listed.csv",
    "AMEX": "https://raw.githubusercontent.com/datasets/amex-listed/master/data/amex-listed.csv",
}

ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")  # optional, for extra redundancy


# =====================================================
# MAIN FUNCTION
# =====================================================
def get_all_us_tickers(force_refresh=False):
    """
    Fetch all U.S. tickers from NASDAQ, NYSE, and AMEX.
    - Uses HTTPS sources (DataHub + GitHub mirrors).
    - Caches locally for 30 days.
    - Falls back to AlphaVantage or static list if needed.
    """
    os.makedirs("data", exist_ok=True)

    # 1. Use cached version if recent and not forced
    if not force_refresh and os.path.exists(CACHE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(CACHE_FILE))
        if datetime.now() - mtime < timedelta(days=CACHE_MAX_AGE_DAYS):
            df = pd.read_csv(CACHE_FILE)
            tickers = sorted(df["Symbol"].unique().tolist())
            print(f"✅ Loaded {len(tickers)} cached tickers (updated {mtime.date()})")
            return tickers
        else:
            print("🔁 Cache older than 30 days — refreshing...")

    # 2. Try pulling from all online sources
    all_tickers = []
    for name, url in DATA_SOURCES.items():
        try:
            print(f"🔍 Fetching {name} listings...")
            df = pd.read_csv(url)
            if "Symbol" in df.columns:
                all_tickers.extend(df["Symbol"].dropna().unique().tolist())
            elif "symbol" in df.columns:
                all_tickers.extend(df["symbol"].dropna().unique().tolist())
        except Exception as e:
            print(f"⚠️ Could not fetch {name} listings: {e}")

    # 3. If still empty, try Alpha Vantage (optional)
    if not all_tickers and ALPHAVANTAGE_API_KEY:
        try:
            print("🔍 Fetching from AlphaVantage LISTING_STATUS...")
            url = f"https://www.alphavantage.co/query?function=LISTING_STATUS&apikey={ALPHAVANTAGE_API_KEY}"
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            df = pd.read_csv(pd.compat.StringIO(r.text))
            if "symbol" in df.columns:
                all_tickers.extend(df["symbol"].dropna().unique().tolist())
        except Exception as e:
            print(f"⚠️ AlphaVantage fetch failed: {e}")

    # 4. Save cache or fallback
    if all_tickers:
        tickers = sorted(set(all_tickers))
        pd.DataFrame({"Symbol": tickers}).to_csv(CACHE_FILE, index=False)
        print(f"💾 Cached {len(tickers)} tickers to {CACHE_FILE}")
        return tickers

    # 5. Final fallback list (static core)
    print("⚠️ All online sources failed, using static fallback...")
    fallback = [
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX",
        "CRM", "INTC", "AVGO", "CSCO", "ORCL", "ADBE", "PYPL", "QCOM", "IBM",
        "BABA", "KO", "PEP", "COST", "MCD", "NKE", "XOM", "CVX", "UNH", "JNJ",
        "PFE", "V", "MA", "WMT"
    ]
    return fallback


# =====================================================
# QUICK TEST
# =====================================================
if __name__ == "__main__":
    tickers = get_all_us_tickers()
    print(f"\nFetched {len(tickers)} tickers (sample): {tickers[:25]}")
