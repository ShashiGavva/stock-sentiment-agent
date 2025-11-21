"""
Quick training script using existing data
"""
import os
import pickle
import pandas as pd
import numpy as np
from lightgbm import LGBMClassifier, LGBMRegressor
import config

print("=" * 70)
print("QUICK TRAINING USING EXISTING DATA")
print("=" * 70)

# Load existing training data
print("\n1. Loading existing training data...")
df = pd.read_csv("data/training_dataset_full.csv")
print(f"✅ Loaded {len(df)} rows")
print(f"   Columns: {list(df.columns)}")

# Recalculate target with new 8% threshold
print(f"\n2. Recalculating target with {config.TARGET_UPSIDE*100}% threshold...")
df["target_hit"] = (df["future_return_10d"] >= config.TARGET_UPSIDE).astype(int)

# Remove old target column
if "target_11pct" in df.columns:
    df = df.drop(columns=["target_11pct"])

print(f"   Target distribution:")
print(f"   - Hit target: {df['target_hit'].sum()} ({df['target_hit'].mean()*100:.1f}%)")
print(f"   - Missed: {(~df['target_hit'].astype(bool)).sum()} ({(1-df['target_hit'].mean())*100:.1f}%)")

# Prepare features
print(f"\n3. Preparing features...")
drop_cols = ["future_return_10d", "target_hit", "date", "symbol"]
X = df.drop(columns=drop_cols, errors="ignore")
X = X.select_dtypes(include=[np.number])  # Only numeric features
y = df["target_hit"]

print(f"   Features: {X.shape[1]}")
print(f"   Feature names: {list(X.columns)}")

# Train classifier
print(f"\n4. Training classifier...")
clf = LGBMClassifier(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1
)
clf.fit(X, y)
print(f"✅ Classifier trained")

# Train regressor
print(f"\n5. Training regressor (q90)...")
reg = LGBMRegressor(
    n_estimators=300,
    max_depth=6,
    learning_rate=0.05,
    objective="quantile",
    alpha=0.9,
    random_state=42,
    verbose=-1
)
reg.fit(X, df["future_return_10d"])
print(f"✅ Regressor trained")

# Save models
print(f"\n6. Saving models...")
os.makedirs("models", exist_ok=True)

with open(config.CLF_PATH, "wb") as f:
    pickle.dump({"model": clf, "features": X.columns.tolist()}, f)
print(f"   ✅ Saved classifier: {config.CLF_PATH}")

with open(config.Q90_PATH, "wb") as f:
    pickle.dump({"model": reg, "features": X.columns.tolist()}, f)
print(f"   ✅ Saved regressor: {config.Q90_PATH}")

print(f"\n" + "=" * 70)
print(f"SUCCESS! Models trained and saved")
print(f"=" * 70)
print(f"\nModels:")
print(f"  - {config.CLF_PATH}")
print(f"  - {config.Q90_PATH}")
print(f"\nNOTE: Models trained WITHOUT sentiment features (21 features)")
print(f"      Daily signals should disable sentiment too: include_sentiment=False")
