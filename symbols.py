import os
import time
import pandas as pd
import requests
from datetime import datetime, timedelta

# =====================================================
# CONFIG
# =====================================================
CACHE_FILE = "data/us_tickers.csv"
SP500_CACHE_FILE = "data/sp500_tickers.csv"
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


def get_sp500_tickers(force_refresh=False):
    """
    Fetch S&P 500 tickers from Wikipedia.
    - More reliable than all US tickers
    - Better data quality (liquid, established companies)
    - Caches locally for 30 days

    Returns:
        list: S&P 500 ticker symbols
    """
    os.makedirs("data", exist_ok=True)

    # 1. Use cached version if recent and not forced
    if not force_refresh and os.path.exists(SP500_CACHE_FILE):
        mtime = datetime.fromtimestamp(os.path.getmtime(SP500_CACHE_FILE))
        if datetime.now() - mtime < timedelta(days=CACHE_MAX_AGE_DAYS):
            df = pd.read_csv(SP500_CACHE_FILE)
            tickers = sorted(df["Symbol"].unique().tolist())
            print(f"✅ Loaded {len(tickers)} cached S&P 500 tickers (updated {mtime.date()})")
            return tickers
        else:
            print("🔁 S&P 500 cache older than 30 days — refreshing...")

    # 2. Fetch from Wikipedia
    try:
        print("🔍 Fetching S&P 500 list from Wikipedia...")
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

        # Read tables from Wikipedia page
        tables = pd.read_html(url)
        df = tables[0]  # First table contains the constituents

        # Extract tickers (Symbol column)
        if 'Symbol' in df.columns:
            tickers = df['Symbol'].tolist()
        elif 'Ticker symbol' in df.columns:
            tickers = df['Ticker symbol'].tolist()
        else:
            # Fallback - first column is usually the ticker
            tickers = df.iloc[:, 0].tolist()

        # Clean tickers (remove any special characters, dots, etc.)
        tickers = [str(t).strip().replace('.', '-') for t in tickers if pd.notna(t)]
        tickers = sorted(set(tickers))

        # Save cache
        pd.DataFrame({"Symbol": tickers}).to_csv(SP500_CACHE_FILE, index=False)
        print(f"💾 Cached {len(tickers)} S&P 500 tickers to {SP500_CACHE_FILE}")

        return tickers

    except Exception as e:
        print(f"⚠️ Could not fetch S&P 500 from Wikipedia: {e}")

        # Fallback to cached file if exists (even if stale)
        if os.path.exists(SP500_CACHE_FILE):
            print("📂 Using stale cache as fallback...")
            df = pd.read_csv(SP500_CACHE_FILE)
            tickers = sorted(df["Symbol"].unique().tolist())
            print(f"✅ Loaded {len(tickers)} tickers from stale cache")
            return tickers

        # Ultimate fallback - core S&P 500 tech stocks
        print("⚠️ Using minimal fallback list...")
        fallback_sp500 = [
            # Tech
            "AAPL", "MSFT", "NVDA", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "AVGO", "ORCL",
            "AMD", "CRM", "CSCO", "ADBE", "ACN", "IBM", "INTC", "QCOM", "TXN", "AMAT",
            "INTU", "NOW", "MU", "ADI", "LRCX", "KLAC", "SNPS", "CDNS", "MCHP", "FTNT",
            # Finance
            "JPM", "BAC", "WFC", "GS", "MS", "BLK", "C", "SCHW", "AXP", "CB",
            # Healthcare
            "UNH", "JNJ", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "PFE", "BMY",
            # Consumer
            "WMT", "HD", "DIS", "MCD", "NKE", "COST", "SBUX", "TGT", "LOW", "TJX",
            # Energy
            "XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL",
            # Industrials
            "BA", "CAT", "GE", "RTX", "HON", "UPS", "DE", "MMM", "LMT", "GD"
        ]
        return sorted(fallback_sp500)


# =====================================================
# QUICK TEST
# =====================================================
if __name__ == "__main__":
    print("\n=== Testing All US Tickers ===")
    tickers = get_all_us_tickers()
    print(f"Fetched {len(tickers)} tickers (sample): {tickers[:25]}")

    print("\n=== Testing S&P 500 Tickers ===")
    sp500 = get_sp500_tickers()
    print(f"Fetched {len(sp500)} S&P 500 tickers (sample): {sp500[:25]}")
