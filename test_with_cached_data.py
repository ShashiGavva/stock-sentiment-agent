"""
Test signal generation using cached training data (avoids Yahoo Finance 403 errors)
"""
import pandas as pd
import numpy as np
import pickle
from features import build_features
import config

print("=" * 70)
print("TESTING SIGNAL GENERATION WITH CACHED DATA")
print("=" * 70)

# Load models
print(f"\n1. Loading models...")
try:
    with open(config.CLF_PATH, "rb") as f:
        clf_pack = pickle.load(f)
    with open(config.Q90_PATH, "rb") as f:
        reg_pack = pickle.load(f)
    clf = clf_pack["model"]
    reg = reg_pack["model"]
    print(f"✅ Models loaded successfully")
    print(f"   Classifier features: {len(clf_pack['features'])}")
    print(f"   Regressor features: {len(reg_pack['features'])}")
except FileNotFoundError as e:
    print(f"❌ Models not found: {e}")
    exit(1)

# Load existing training data
print(f"\n2. Loading cached training data...")
df_full = pd.read_csv("data/training_dataset_full.csv")
print(f"✅ Loaded {len(df_full)} rows")

# Get latest data point for each stock
print(f"\n3. Testing each stock's latest prediction...")
test_results = []

for symbol in df_full['symbol'].unique():
    df_stock = df_full[df_full['symbol'] == symbol].copy()

    # Get last row features
    last_row = df_stock.iloc[-1:]

    # Prepare features
    drop_cols = ["future_return_10d", "target_11pct", "target_hit", "date", "symbol"]
    X = last_row.drop(columns=drop_cols, errors="ignore")
    X = X.select_dtypes(include=[np.number])

    # Get predictions
    try:
        proba = clf.predict_proba(X)[0, 1]
        pred_q90 = reg.predict(X)[0]

        test_results.append({
            'symbol': symbol,
            'probability': proba,
            'pred_q90': pred_q90,
            'passes_threshold': proba >= config.CONFIDENCE_TIERS['medium']
        })
    except Exception as e:
        print(f"   ❌ {symbol}: {e}")

# Display results
print(f"\n" + "=" * 70)
print(f"RESULTS")
print(f"=" * 70)

print(f"\nThreshold: {config.CONFIDENCE_TIERS['medium']*100}%")
print(f"\n{'Symbol':<10} {'Probability':<15} {'Q90 Return':<15} {'Signal?':<10}")
print("-" * 70)

for result in sorted(test_results, key=lambda x: x['probability'], reverse=True):
    signal = "✅ YES" if result['passes_threshold'] else "❌ NO"
    print(f"{result['symbol']:<10} {result['probability']*100:>6.1f}%        {result['pred_q90']*100:>7.2f}%           {signal}")

signals_count = sum(1 for r in test_results if r['passes_threshold'])
print(f"\n" + "=" * 70)
print(f"SUMMARY: {signals_count} out of {len(test_results)} stocks pass threshold")
print(f"=" * 70)

if signals_count == 0:
    print(f"\n⚠️ WARNING: No signals generated!")
    print(f"\nPossible reasons:")
    print(f"  1. Threshold too high ({config.CONFIDENCE_TIERS['medium']*100}%)")
    print(f"  2. Model predictions are low for current market")
    print(f"  3. Training data is stale")
    print(f"\nTry lowering threshold in config.py:")
    print(f"  CONFIDENCE_TIERS = {{'medium': 0.50}}  # Instead of {config.CONFIDENCE_TIERS['medium']}")
else:
    print(f"\n✅ SUCCESS! Signal generation is working correctly")
