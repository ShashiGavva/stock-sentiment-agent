# Setup Instructions for Day Trading Automation

## Prerequisites

Before running the automation, you need to train the ML models first.

## Step-by-Step Setup

### 1. Train ML Models (Required - First Time Only)

The automation requires trained ML models. Run the training script:

```bash
source .venv312/bin/activate
python train_models.py
```

This will create:
- `models/clf_lgbm_08.pkl` - Classification model
- `models/reg_q90_08.pkl` - Regression model

**Note**: Training may take 10-30 minutes depending on your dataset size.

### 2. Test the Setup

Run the test script to verify everything is configured correctly:

```bash
python test_automation.py
```

All checks should pass (✅) before proceeding.

### 3. Test Individual Components (Optional)

Before starting the full automation, test individual components:

```bash
# Test signal generation (should take a few minutes)
python daily_signals.py

# Verify signals were generated
cat data/daily_signals.csv | head -20
```

### 4. Start Automation

Once models are trained and tests pass:

```bash
# Option A: Run as background service (recommended)
./start_automation.sh

# Option B: Run in foreground for testing
./run_automation_foreground.sh
```

### 5. Monitor and Verify

Check logs to ensure it's working:

```bash
# View real-time logs
tail -f logs/automation.log

# Check for errors
tail -f logs/automation.error.log

# View today's watchlist (after 8:30 AM CST)
cat data/automation_watchlist.json

# View active positions
cat data/automation_positions.json

# View today's digest (after 3:00 PM CST)
cat data/daily_digest.txt
```

## Troubleshooting

### Models Not Found Error

If you see:
```
❌ Classification model not found: models/clf_lgbm_08.pkl
```

**Solution**: Run the training script first:
```bash
python train_models.py
```

### Import Errors

If you see import errors, ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Schedule Not Running

Make sure you're in the correct timezone (CST) and it's a weekday:
```bash
# Check current time
date

# The automation only runs Monday-Friday
# Signal generation: 8:30 AM CST
# Trading: 9:00 AM - 3:00 PM CST (every 5 minutes)
# Digest: 3:00 PM CST
```

### Service Won't Start

```bash
# Stop any existing service
./stop_automation.sh

# Check for errors
cat logs/automation.error.log

# Try running in foreground to see errors directly
./run_automation_foreground.sh
```

## Quick Reference

| Command | Description |
|---------|-------------|
| `python train_models.py` | Train ML models (required first time) |
| `python test_automation.py` | Test setup and configuration |
| `./start_automation.sh` | Start automation service |
| `./stop_automation.sh` | Stop automation service |
| `./run_automation_foreground.sh` | Run in foreground for debugging |
| `tail -f logs/automation.log` | View real-time logs |
| `launchctl list \| grep daytrading` | Check service status |

## Files and Directories

### Created During Setup
- `models/` - ML model files (created by train_models.py)
- `logs/` - Log files (created automatically)
- `data/automation_watchlist.json` - Daily top 10 stocks
- `data/automation_positions.json` - Current open positions
- `data/automation_trades.json` - Today's trades
- `data/daily_digest.txt` - End-of-day summary

### Configuration Files
- `config.py` - Trading parameters and thresholds
- `automation_scheduler.py` - Main scheduler logic
- `com.daytrading.automation.plist` - macOS service configuration

## Customization

### Adjust Trading Amounts

Edit `automation_scheduler.py`:

```python
INITIAL_INVESTMENT = 1000      # First buy (default: $1000)
SUBSEQUENT_INVESTMENT = 250    # Additional buys (default: $250)
MAX_POSITION_SIZE = 3000       # Max per stock (default: $3000)
```

### Change Signal Selection

The automation uses top 10 signals by default. To change this, edit `generate_daily_signals()` in `automation_scheduler.py`:

```python
# Get top 10 signals for watchlist
top_10 = df_out.head(10)['symbol'].tolist()  # Change 10 to your preferred number
```

### Adjust Confidence Threshold

Edit `config.py`:

```python
CONFIDENCE_TIERS = {
    'high': 0.70,      # High confidence signals (70%+)
    'medium': 0.60,    # Medium confidence (60-70%)
    'low': 0.50        # Low confidence (50-60%)
}
```

The automation uses 'medium' threshold (60%) by default.

## Next Steps

For detailed automation information, see `AUTOMATION_README.md`.

For connecting to a real broker API, you'll need to:
1. Choose a broker (Alpaca, Interactive Brokers, etc.)
2. Install their SDK
3. Modify `execute_trade()` function in `automation_scheduler.py`
4. Add API credentials and authentication
