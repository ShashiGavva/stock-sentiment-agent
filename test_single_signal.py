"""
Diagnostic: Why are 0 signals being generated?
Test a single stock to see what's happening.
"""

import pandas as pd
import numpy as np
import pickle
from features import build_features
from daily_signals import fetch_data
import config

print("=" * 70)
print("TESTING SIGNAL GENERATION ON SINGLE STOCK")
print("=" * 70)

# Test with a known volatile stock
test_symbol = "NVDA"

print(f"\n1. Loading models...")
try:
    with open(config.CLF_PATH, "rb") as f:
        clf_pack = pickle.load(f)
    with open(config.Q90_PATH, "rb") as f:
        reg_pack = pickle.load(f)
    clf = clf_pack["model"]
    reg = reg_pack["model"]
    print(f"✅ Models loaded successfully")
    print(f"   Classifier: {config.CLF_PATH}")
    print(f"   Regressor: {config.Q90_PATH}")
except FileNotFoundError as e:
    print(f"❌ Models not found: {e}")
    print(f"\nYou need to force retrain:")
    print(f"  rm models/clf_lgbm_08.pkl models/reg_q90_08.pkl")
    print(f"  python train_models.py")
    exit(1)

print(f"\n2. Fetching data for {test_symbol}...")
df = fetch_data(test_symbol, period="3mo")
if df is None:
    print(f"❌ Could not fetch data for {test_symbol}")
    exit(1)
print(f"✅ Fetched {len(df)} days of data")

print(f"\n3. Building features (WITHOUT sentiment - matching model)...")
feats = build_features(df, symbol=test_symbol, include_sentiment=False)
if feats is None or feats.empty:
    print(f"❌ Could not build features")
    exit(1)

print(f"✅ Built features: {len(feats)} rows")
print(f"   Columns: {list(feats.columns)}")
print(f"   Total features: {len(feats.columns)}")
print(f"   NOTE: Sentiment features disabled (models trained without sentiment)")

print(f"\n4. Preparing features for prediction...")
drop_cols = ["future_return_10d", "target_hit", "date", "symbol"]
X = feats.drop(columns=drop_cols, errors="ignore").select_dtypes(include=[np.number]).iloc[-1:]

print(f"   Feature count for model: {X.shape[1]}")
print(f"   Features: {list(X.columns)}")

# Check for NaN/inf
if X.isna().any().any():
    print(f"   ⚠️ WARNING: NaN values found!")
    print(X.isna().sum())
if np.isinf(X.values).any():
    print(f"   ⚠️ WARNING: Inf values found!")

print(f"\n5. Getting predictions...")
try:
    proba = clf.predict_proba(X)[0, 1]
    pred_q90 = reg.predict(X)[0]

    print(f"✅ Predictions successful:")
    print(f"   Probability of {config.TARGET_UPSIDE*100}% gain: {proba:.3f} ({proba*100:.1f}%)")
    print(f"   Predicted Q90 return: {pred_q90*100:.2f}%")
    print(f"   Latest close: ${feats['close'].iloc[-1]:.2f}")
except Exception as e:
    print(f"❌ Prediction failed: {e}")
    exit(1)

print(f"\n6. Checking threshold...")
threshold = config.CONFIDENCE_TIERS['medium']
print(f"   Threshold: {threshold:.2f} ({threshold*100}%)")
print(f"   Probability: {proba:.3f} ({proba*100:.1f}%)")

if proba >= threshold:
    print(f"   ✅ PASSES - Would generate signal")
else:
    print(f"   ❌ FAILS - Probability too low")
    print(f"   Need: {threshold:.2f}, Got: {proba:.3f}")
    print(f"   Gap: {(threshold - proba):.3f} ({(threshold - proba)*100:.1f}%)")

print(f"\n" + "=" * 70)
print("DIAGNOSIS:")
print("=" * 70)

if proba < 0.1:
    print("""
❌ VERY LOW PROBABILITY (<10%)

Possible causes:
1. Model not trained properly (features might be wrong)
2. Sentiment features causing issues
3. Feature values are unusual/outliers

Try:
  1. Check if sentiment is working: all values should not be 0
  2. Retrain without sentiment: set include_sentiment=False in features.py
  3. Check feature distributions in training data
""")
elif proba < threshold:
    print(f"""
⚠️ LOW PROBABILITY ({proba*100:.1f}% < {threshold*100}%)

The model IS working but this stock doesn't meet threshold.

Options:
1. Lower threshold in config.py:
   CONFIDENCE_TIERS = {{'medium': 0.50}}  # Instead of 0.60

2. Try different stocks - maybe current market has few opportunities

3. Check if 8% target is too conservative - try 6%:
   TARGET_UPSIDE = 0.06
   Then retrain
""")
else:
    print(f"""
✅ PROBABILITY PASSES ({proba*100:.1f}% >= {threshold*100}%)

Model is working! This stock would generate a signal.

If daily_signals.py still shows 0 signals, the issue is:
- Sentiment fetching is timing out for many stocks
- Most S&P 500 stocks don't meet current threshold
- Try running with less stocks or lower threshold
""")
