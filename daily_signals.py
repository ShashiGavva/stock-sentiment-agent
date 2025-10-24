import os, pickle
from datetime import datetime
import numpy as np, pandas as pd, yfinance as yf

from config import (HORIZON_DAYS, TARGET_UPSIDE, ENTRY_BUFFER, STOP_ATR_MULT, RISK_REWARD,
                    MIN_ATR_PCT, MIN_DOLLAR_VOL, DATA_DIR, CLF_PATH, Q90_PATH)
from features import add_tech_features

# === pull your universe from symbols.py ===
def load_symbols() -> list[str]:
    try:
        import symbols
        if hasattr(symbols, "get_symbols"):
            return [s.upper() for s in symbols.get_symbols()]
        if hasattr(symbols, "TICKERS"):
            return [str(s).upper() for s in symbols.TICKERS]
    except Exception:
        pass
    return ["AAPL","MSFT","NVDA","CRNC"]  # fallback

def fetch_latest(symbols: list[str]) -> pd.DataFrame:
    bag = {}
    for s in symbols:
        try:
            df = yf.download(s, period="6mo", interval="1d", auto_adjust=False, progress=False)
            if df.empty: 
                continue
            df = df.rename_axis("Date").reset_index()
            df = df[['Date','Open','High','Low','Close','Volume']]
            df = add_tech_features(df).dropna()
            bag[s] = df.iloc[-1]
        except Exception:
            pass
    if not bag:
        raise RuntimeError("No fresh data pulled.")
    return pd.DataFrame(bag).T

def compute_levels(row: pd.Series) -> pd.Series:
    px = float(row['Close'])
    entry = px * (1 + ENTRY_BUFFER)
    stop = max(entry - STOP_ATR_MULT*float(row['ATR14']), px * 0.97)
    target = max(entry * (1 + TARGET_UPSIDE), entry + RISK_REWARD * (entry - stop))
    return pd.Series({'entry': round(entry,4), 'stop': round(stop,4), 'target': round(target,4)})

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    # load models
    with open(CLF_PATH, "rb") as f: clf_pack = pickle.load(f)
    with open(Q90_PATH, "rb") as f: q90_pack = pickle.load(f)
    clf, thr = clf_pack['model'], clf_pack['meta']['threshold']
    reg = q90_pack['model']; FEATS = clf_pack['meta']['feature_cols']

    syms = load_symbols()
    live = fetch_latest(syms)
    live['atrp'] = (live['ATR14'] / live['Close']).clip(upper=0.25)
    live['DollarVol'] = live['Close'] * live['Volume']

    X = live[FEATS].astype(float)
    p = clf.predict_proba(X)[:,1]
    r90 = reg.predict(X)

    picks = live.assign(prob=p, q90=r90)
    picks = picks[(picks['prob'] >= thr) &
                  (picks['q90'] >= TARGET_UPSIDE) &
                  (picks['atrp'] >= MIN_ATR_PCT) &
                  (picks['DollarVol'] >= MIN_DOLLAR_VOL)].copy()

    if picks.empty:
        print("No candidates met 11% criteria today.")
        return

    levels = picks.apply(compute_levels, axis=1)
    out = pd.concat([picks[['prob','q90','Close','ATR14','DollarVol']], levels], axis=1)
    out = out.sort_values('prob', ascending=False)

    ts = datetime.now().strftime('%Y-%m-%d_%H%M')
    out_path = os.path.join(DATA_DIR, f"signals_{ts}.csv")
    out.to_csv(out_path, index=True)  # index is symbol
    print("Saved:", out_path)

    # ---- OPTIONAL: send email using your existing module ----
    try:
        from send_signals_email import send_signals_email  # adjust if your function name differs
        send_signals_email(csv_path=out_path, subject=f"Daily Signals {ts}", html_template="templates/email_long_only.html")
    except Exception as e:
        print("Email step skipped:", e)

if __name__ == "__main__":
    main()
