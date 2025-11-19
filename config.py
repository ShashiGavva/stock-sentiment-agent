# Core thresholds
HORIZON_DAYS = 10       # look-ahead window
TARGET_UPSIDE = 0.08    # +8% movers (reduced from 11% for more realistic targets)

# Filters
MIN_ATR_PCT = 0.02      # ATR/price >= 2%
MIN_DOLLAR_VOL = 1_000_000  # $ volume floor

# Levels
ENTRY_BUFFER = 0.002    # 0.2% above last close
STOP_ATR_MULT = 1.0     # 1x ATR below entry
RISK_REWARD = 2.0       # 2R target fallback

# Training targets
TARGET_PRECISION = 0.55 # calibrate prob threshold for ≥55% precision (reduced for more signals)

# Model confidence thresholds (for signal generation)
# These should be validated against backtest calibration
CONFIDENCE_TIERS = {
    'high': 0.70,      # High confidence signals (70%+)
    'medium': 0.60,    # Medium confidence (60-70%)
    'low': 0.50        # Low confidence but still tradeable (50-60%)
}

# Paths
DATA_DIR = "data"
MODELS_DIR = "models"
CLF_PATH = f"{MODELS_DIR}/clf_lgbm_08.pkl"  # Updated to reflect 8% target
Q90_PATH = f"{MODELS_DIR}/reg_q90_08.pkl"  # Updated to reflect 8% target
