import os, pickle
import numpy as np, pandas as pd, yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.metrics import average_precision_score, precision_recall_curve
from lightgbm import LGBMClassifier, LGBMRegressor

from config import (HORIZON_DAYS, TARGET_UPSIDE, TARGET_PRECISION,
                    CLF_PATH, Q90_PATH, MODELS_DIR)
from features import add_tech_features, future_max_return

# ---- pull symbols from your existing repo ----
def load_symbols() -> list[str]:
    # symbols.py can expose TICKERS or a function. We support both.
    try:
        import symbols
        if hasattr(symbols, "get_symbols"):
            return [s.upper() for s in symbols.get_symbols()]
        if hasattr(symbols, "TICKERS"):
            return [str(s).upper() for s in symbols.TICKERS]
    except Exception:
        pass
    # fallback small demo universe
    return ["AAPL","MSFT","NVDA","CRNC"]

def yf_hist(sym: str, years: str = "2y") -> pd.DataFrame:
    df = yf.download(sym, period=years, interval="1d", auto_adjust=False, progress=False)
    df = df.rename_axis("Date").reset_index()
    return df[['Date','Open','High','Low','Close','Volume']]

def build_dataset(symbols: list[str]) -> pd.DataFrame:
    frames = []
    for s in symbols:
        try:
            df = yf_hist(s, "2y")
            if df.empty or len(df) < 220:
                continue
            df['Symbol'] = s
            df = add_tech_features(df)
            df['y11'] = (future_max_return(df['Close'], HORIZON_DAYS) >= TARGET_UPSIDE).astype(int)
            df['r_max'] = future_max_return(df['Close'], HORIZON_DAYS)
            frames.append(df.dropna())
        except Exception as e:
            print("skip", s, e)
    if not frames:
        raise RuntimeError("No data built — check connectivity or symbols.py")
    return pd.concat(frames, ignore_index=True)

def train():
    os.makedirs(MODELS_DIR, exist_ok=True)
    syms = load_symbols()[:500]
    data = build_dataset(syms)

    FEATS = ['Open','High','Low','Close','Volume','ATR14','RSI14',
             'MACD','MACDsig','MACDh','Ret1','Ret5',
             'SMA10_pct','SMA50_pct','SMA200_pct','DollarVol']
    X = data[FEATS].astype(float)
    y = data['y11'].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, shuffle=False)

    pos_weight = max(5, int((ytr==0).mean()/(ytr==1).mean()))
    clf = LGBMClassifier(n_estimators=1200, learning_rate=0.02, num_leaves=63,
                         subsample=0.8, colsample_bytree=0.8,
                         class_weight={0:1, 1:pos_weight},
                         reg_alpha=1.0, reg_lambda=2.0)
    clf.fit(Xtr, ytr)
    proba = clf.predict_proba(Xte)[:,1]
    pr_auc = average_precision_score(yte, proba)

    # pick threshold that achieves target precision
    prec, rec, thr = precision_recall_curve(yte, proba)
    chosen = 0.99
    for p, t in zip(prec, np.r_[thr, 1]):
        if p >= TARGET_PRECISION:
            chosen = t; break

    reg_q90 = LGBMRegressor(objective="quantile", alpha=0.9, n_estimators=800, learning_rate=0.03)
    reg_q90.fit(Xtr, data.loc[Xtr.index, 'r_max'])

    meta = {'feature_cols': FEATS, 'threshold': float(chosen), 'pr_auc': float(pr_auc)}
    with open(CLF_PATH, "wb") as f: pickle.dump({'model': clf, 'meta': meta}, f)
    with open(Q90_PATH, "wb") as f: pickle.dump({'model': reg_q90, 'meta': meta}, f)
    print("Saved", CLF_PATH, Q90_PATH, "PR_AUC:", pr_auc, "thr@prec≥", TARGET_PRECISION, "=", chosen)

if __name__ == "__main__":
    train()
