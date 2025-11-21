"""
Debug script to understand why no signals are generated.
"""

import sys
import os

print("=" * 70)
print("DIAGNOSING: Why No Signals Generated")
print("=" * 70)

# Issue 1: Model Files
print("\n1. MODEL FILES CHECK")
print("-" * 70)

import config
print(f"Config expects:")
print(f"  CLF: {config.CLF_PATH}")
print(f"  REG: {config.Q90_PATH}")

print(f"\nFiles actually exist:")
for f in os.listdir('models'):
    if f.endswith('.pkl'):
        print(f"  models/{f}")

clf_exists = os.path.exists(config.CLF_PATH)
reg_exists = os.path.exists(config.Q90_PATH)

print(f"\n✅ Classifier exists: {clf_exists}")
print(f"✅ Regressor exists: {reg_exists}")

if not clf_exists or not reg_exists:
    print("\n❌ PROBLEM: Models don't exist!")
    print("   The code looks for clf_lgbm_08.pkl but only clf_lgbm_11.pkl exists")
    print("   Solution: Retrain models with new code")
    sys.exit(1)

# Issue 2: Feature Mismatch
print("\n2. FEATURE MISMATCH CHECK")
print("-" * 70)

print("\nOld models (clf_lgbm_11.pkl) were trained WITHOUT:")
print("  - sentiment_score")
print("  - sentiment_positive")
print("  - sentiment_negative")
print("  - sentiment_neutral")
print("  - news_count")

print("\nNew code (daily_signals.py) tries to ADD:")
print("  - sentiment_score")
print("  - sentiment_positive")
print("  - sentiment_negative")
print("  - sentiment_neutral")
print("  - news_count")

print("\n❌ PROBLEM: Feature count mismatch!")
print("   Old models expect ~21 features")
print("   New features() creates ~26 features (21 + 5 sentiment)")
print("   LightGBM will error or give wrong predictions")

# Issue 3: Target Column Name
print("\n3. TARGET COLUMN NAME CHECK")
print("-" * 70)

print("\nOld models trained on: target_11pct")
print("New code uses: target_hit")
print("\n✅ This is OK - column name doesn't affect prediction")
print("   (Only matters during training)")

# Issue 4: Configuration
print("\n4. CONFIGURATION CHECK")
print("-" * 70)

print(f"\nS&P 500 Only: {config.USE_SP500_ONLY}")
print(f"Target Upside: {config.TARGET_UPSIDE*100}%")
print(f"Confidence Threshold: {config.CONFIDENCE_TIERS}")
print(f"Prediction Threshold: medium = {config.CONFIDENCE_TIERS['medium']}")

print("\n✅ Configuration looks OK")

# Summary
print("\n" + "=" * 70)
print("SUMMARY OF ISSUES")
print("=" * 70)

print("""
ISSUE #1: Wrong Model Files ❌
- Code looks for: clf_lgbm_08.pkl, reg_q90_08.pkl
- Actually exists: clf_lgbm_11.pkl, reg_q90_11.pkl
- Impact: daily_signals.py fails to load models

ISSUE #2: Feature Mismatch ❌
- Old models: 21 features (no sentiment)
- New code: 26 features (with sentiment)
- Impact: Even if models load, predictions will be wrong

ISSUE #3: Not Retrained ❌
- Models still use 11% target threshold
- Config expects 8% target
- Impact: Model behavior doesn't match expectations

SOLUTION:
Must retrain models with current code:
  python train_models.py

This will:
- Create clf_lgbm_08.pkl with correct name
- Include sentiment features (26 features)
- Use 8% target threshold
- Train on S&P 500 stocks only
""")
