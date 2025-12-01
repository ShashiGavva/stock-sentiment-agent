#!/usr/bin/env python3
"""
Weekly ML Retraining Module
Retrains models based on actual trades from the past week.
"""

import os
import json
import pickle
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from features import build_features
import config


# =====================================================
# CONFIG
# =====================================================
TRADE_HISTORY_FILE = "data/trade_history.json"
CLF_PATH = config.CLF_PATH
REG_PATH = config.Q90_PATH
BACKUP_SUFFIX = ".backup"
MIN_TRADES_FOR_RETRAIN = 10  # Minimum trades needed before retraining


# =====================================================
# LOAD TRADE HISTORY
# =====================================================
def load_trade_history(days=7):
    """Load trades from the past N days."""
    if not os.path.exists(TRADE_HISTORY_FILE):
        print("⚠️ No trade history found")
        return []

    with open(TRADE_HISTORY_FILE, 'r') as f:
        all_trades = json.load(f)

    # Filter to past N days
    cutoff_date = datetime.now() - timedelta(days=days)
    recent_trades = [
        t for t in all_trades
        if datetime.fromisoformat(t['entry_time']) >= cutoff_date
    ]

    print(f"📊 Loaded {len(recent_trades)} trades from past {days} days")
    return recent_trades


# =====================================================
# PREPARE TRAINING DATA FROM TRADES
# =====================================================
def prepare_training_data_from_trades(trades):
    """
    Convert trade history into training data.

    For each trade:
    - Fetch historical data at entry time
    - Build features as they were at entry
    - Label as success/failure based on actual P&L
    """
    training_samples = []

    for trade in trades:
        try:
            symbol = trade['symbol']
            entry_time = datetime.fromisoformat(trade['entry_time'])
            entry_price = trade['buy_price']
            exit_price = trade['sell_price']
            profit_loss_pct = trade['profit_loss_percent']

            # Fetch historical data (need data before entry for feature calculation)
            # Get 6 months of data to ensure we have enough for indicators
            end_date = entry_time
            start_date = end_date - timedelta(days=180)

            df = yf.download(
                symbol,
                start=start_date.strftime('%Y-%m-%d'),
                end=end_date.strftime('%Y-%m-%d'),
                progress=False,
                auto_adjust=True
            )

            if df.empty or len(df) < 60:  # Need at least 60 days for indicators
                print(f"⚠️ Insufficient data for {symbol}")
                continue

            # Standardize column names
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

            # Filter to required columns only
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            df = df[[col for col in required_cols if col in df.columns]]

            # Build features (without sentiment)
            feats = build_features(df, symbol=symbol, include_sentiment=False)
            if feats is None or feats.empty:
                print(f"⚠️ Could not build features for {symbol}")
                continue

            # Get features at entry time (last row)
            X = feats.drop(
                columns=["future_return_10d", "target_hit", "date", "symbol"],
                errors="ignore"
            ).select_dtypes(include=[np.number]).iloc[-1:]

            if X.empty:
                continue

            # Label based on actual outcome
            # Success = profit >= 8% (matching our model's target)
            target_threshold = 0.08  # 8% target
            is_success = 1 if profit_loss_pct >= (target_threshold * 100) else 0

            # For regression: use actual return as target
            actual_return = (exit_price - entry_price) / entry_price

            training_samples.append({
                'features': X,
                'classification_target': is_success,
                'regression_target': actual_return,
                'symbol': symbol,
                'entry_time': entry_time,
                'profit_loss_pct': profit_loss_pct
            })

            print(f"✅ {symbol}: {profit_loss_pct:+.2f}% → {'SUCCESS' if is_success else 'FAIL'}")

        except Exception as e:
            print(f"⚠️ Error processing {trade.get('symbol', 'unknown')}: {e}")
            continue

    return training_samples


# =====================================================
# RETRAIN MODELS
# =====================================================
def retrain_models(training_samples):
    """Retrain models using new trade data."""
    if len(training_samples) < MIN_TRADES_FOR_RETRAIN:
        print(f"⚠️ Only {len(training_samples)} trades available. Need at least {MIN_TRADES_FOR_RETRAIN} for retraining.")
        return False

    # Load existing models
    print("\n📦 Loading existing models...")
    with open(CLF_PATH, 'rb') as f:
        clf_pack = pickle.load(f)
    with open(REG_PATH, 'rb') as f:
        reg_pack = pickle.load(f)

    clf = clf_pack['model']
    reg = reg_pack['model']

    # Prepare training data
    X_list = [s['features'] for s in training_samples]
    y_clf = [s['classification_target'] for s in training_samples]
    y_reg = [s['regression_target'] for s in training_samples]

    X = pd.concat(X_list, ignore_index=True)
    y_clf = np.array(y_clf)
    y_reg = np.array(y_reg)

    print(f"\n📊 Training data: {len(X)} samples")
    print(f"   Success rate: {y_clf.mean()*100:.1f}%")
    print(f"   Avg return: {y_reg.mean()*100:+.2f}%")

    # Backup existing models
    print("\n💾 Backing up existing models...")
    os.makedirs("models", exist_ok=True)
    if os.path.exists(CLF_PATH):
        backup_clf = CLF_PATH + BACKUP_SUFFIX
        with open(CLF_PATH, 'rb') as src, open(backup_clf, 'wb') as dst:
            dst.write(src.read())
        print(f"   Backed up classifier to {backup_clf}")

    if os.path.exists(REG_PATH):
        backup_reg = REG_PATH + BACKUP_SUFFIX
        with open(REG_PATH, 'rb') as src, open(backup_reg, 'wb') as dst:
            dst.write(src.read())
        print(f"   Backed up regressor to {backup_reg}")

    # Incremental training (warm start)
    print("\n🔄 Retraining classifier...")
    try:
        # LightGBM doesn't support warm start, so we retrain from scratch
        # but we can use the previous model's parameters
        clf_params = clf.get_params()
        new_clf = LGBMClassifier(**clf_params)
        new_clf.fit(X, y_clf)

        # Evaluate on training set (just for monitoring)
        y_pred = new_clf.predict(X)
        y_proba = new_clf.predict_proba(X)[:, 1]

        acc = accuracy_score(y_clf, y_pred)
        prec = precision_score(y_clf, y_pred, zero_division=0)
        rec = recall_score(y_clf, y_pred, zero_division=0)
        auc = roc_auc_score(y_clf, y_proba) if len(np.unique(y_clf)) > 1 else 0

        print(f"   Accuracy: {acc:.3f}")
        print(f"   Precision: {prec:.3f}")
        print(f"   Recall: {rec:.3f}")
        print(f"   AUC: {auc:.3f}")

        # Save updated classifier
        clf_pack['model'] = new_clf
        clf_pack['last_retrain'] = datetime.now().isoformat()
        clf_pack['retrain_samples'] = len(X)

        with open(CLF_PATH, 'wb') as f:
            pickle.dump(clf_pack, f)
        print(f"✅ Updated classifier saved to {CLF_PATH}")

    except Exception as e:
        print(f"❌ Classifier retraining failed: {e}")
        return False

    # Retrain regressor
    print("\n🔄 Retraining regressor...")
    try:
        reg_params = reg.get_params()
        new_reg = LGBMRegressor(**reg_params)
        new_reg.fit(X, y_reg)

        # Evaluate
        y_pred_reg = new_reg.predict(X)
        rmse = np.sqrt(np.mean((y_reg - y_pred_reg)**2))
        mae = np.mean(np.abs(y_reg - y_pred_reg))

        print(f"   RMSE: {rmse:.4f}")
        print(f"   MAE: {mae:.4f}")

        # Save updated regressor
        reg_pack['model'] = new_reg
        reg_pack['last_retrain'] = datetime.now().isoformat()
        reg_pack['retrain_samples'] = len(X)

        with open(REG_PATH, 'wb') as f:
            pickle.dump(reg_pack, f)
        print(f"✅ Updated regressor saved to {REG_PATH}")

    except Exception as e:
        print(f"❌ Regressor retraining failed: {e}")
        return False

    return True


# =====================================================
# MAIN
# =====================================================
def main(days=7):
    """
    Main weekly retraining workflow.

    Args:
        days: Number of days of trade history to use (default: 7 for weekly)
    """
    print("=" * 60)
    print("📚 WEEKLY ML MODEL RETRAINING")
    print("=" * 60)

    # Load trades from past week
    trades = load_trade_history(days=days)

    if not trades:
        print("❌ No trades to train on")
        return

    # Prepare training data
    print("\n🔧 Preparing training data from trades...")
    training_samples = prepare_training_data_from_trades(trades)

    if not training_samples:
        print("❌ No valid training samples generated")
        return

    # Retrain models
    success = retrain_models(training_samples)

    if success:
        print("\n" + "=" * 60)
        print("✅ RETRAINING COMPLETE")
        print("=" * 60)
        print(f"   Models updated based on {len(training_samples)} trades")
        print(f"   Backups saved with {BACKUP_SUFFIX} extension")
        print(f"   Next run: {(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')}")
    else:
        print("\n" + "=" * 60)
        print("❌ RETRAINING FAILED")
        print("=" * 60)


if __name__ == "__main__":
    import sys

    # Allow custom days via command line: python weekly_retrain.py 14
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7

    print(f"Using trades from past {days} days\n")
    main(days=days)
