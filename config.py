# Core thresholds
HORIZON_DAYS = 10       # look-ahead window
TARGET_UPSIDE = 0.11    # +11% movers only

# Filters
MIN_ATR_PCT = 0.02      # ATR/price >= 2%
MIN_DOLLAR_VOL = 1_000_000  # $ volume floor

# Levels
ENTRY_BUFFER = 0.002    # 0.2% above last close
STOP_ATR_MULT = 1.0     # 1x ATR below entry
RISK_REWARD = 2.0       # 2R target fallback

# Training targets
TARGET_PRECISION = 0.60 # calibrate prob threshold for ≥60% precision on 11% movers

# Paths
DATA_DIR = "data"
MODELS_DIR = "models"
CLF_PATH = f"{MODELS_DIR}/clf_lgbm_11.pkl"
Q90_PATH = f"{MODELS_DIR}/reg_q90_11.pkl"
