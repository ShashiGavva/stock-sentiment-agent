# Day Trading Automation - Quick Start Guide

## What This Does

Fully automated day trading system that:

1. **8:30 AM CST** - Scans S&P 500, generates signals, picks top 10 stocks
2. **9:00 AM - 3:00 PM CST** - Trades every 5 minutes with your logic:
   - First BUY: Invest $1,000
   - Additional BUYs: Add $250 (max $3,000/stock)
   - SELL: Close entire position
3. **3:00 PM CST** - Sends daily digest with P&L summary

## Quick Start (3 Steps)

### Step 1: Train Models (First Time Only)

```bash
source .venv312/bin/activate
python train_models.py
```

This takes 10-30 minutes. Creates the ML models needed for signal generation.

### Step 2: Verify Setup

```bash
python test_automation.py
```

All checks should show ✅. If you see ❌ for models, run Step 1 first.

### Step 3: Start Automation

```bash
./start_automation.sh
```

That's it! The automation will run continuously in the background.

## Daily Usage

Once started, the automation runs automatically every weekday. No manual intervention needed.

### Check Status

```bash
./view_status.sh
```

Shows:
- Service status (running/stopped)
- Today's watchlist
- Active positions
- Recent trades
- Latest digest

### View Logs

```bash
tail -f logs/automation.log
```

### Stop Automation

```bash
./stop_automation.sh
```

## What Gets Created

All data stored in `data/` directory:

- `automation_watchlist.json` - Top 10 stocks (updated 8:30 AM)
- `automation_positions.json` - Open positions (updated every 5 min)
- `automation_trades.json` - Today's trades (updated every 5 min)
- `daily_digest.txt` - End-of-day summary (updated 3:00 PM)

## Troubleshooting

**Problem**: Models not found
```bash
# Solution: Train models first
python train_models.py
```

**Problem**: Automation won't start
```bash
# Solution: Check logs and restart
./stop_automation.sh
cat logs/automation.error.log
./start_automation.sh
```

**Problem**: No trades executing
```bash
# Check watchlist exists
cat data/automation_watchlist.json

# Verify it's market hours (9 AM - 3 PM CST, weekdays)
date

# Check logs for errors
tail -f logs/automation.log
```

## Files Overview

| File | Purpose |
|------|---------|
| `automation_scheduler.py` | Main automation logic |
| `start_automation.sh` | Start automation |
| `stop_automation.sh` | Stop automation |
| `view_status.sh` | Check current status |
| `test_automation.py` | Verify setup |
| `AUTOMATION_SUMMARY.md` | Detailed documentation |
| `SETUP_INSTRUCTIONS.md` | Detailed setup guide |

## Configuration

Edit `automation_scheduler.py` to adjust:

```python
INITIAL_INVESTMENT = 1000      # First buy: $1000
SUBSEQUENT_INVESTMENT = 250    # Additional: $250
MAX_POSITION_SIZE = 3000       # Max per stock: $3000
```

## Schedule

Runs Monday-Friday only:

| Time | Action |
|------|--------|
| 8:30 AM CST | Generate signals, populate watchlist |
| 9:00 AM CST | Start trading |
| Every 5 min | Process signals, manage positions |
| 3:00 PM CST | Generate digest |

## Example Digest

```
======================================================================
DAY TRADING DIGEST - 2025-12-04
======================================================================

📊 WATCHLIST
AAPL, MSFT, NVDA, TSLA, AMD, GOOGL, META, AMZN, NFLX, AVGO

📈 TRADING ACTIVITY
Total trades: 15 (Buys: 10, Sells: 5)

💰 PERFORMANCE
Total P&L: +$342.50
Win rate: 80.0%

💼 OPEN POSITIONS (5)
  NVDA: 8.5 shares @ $145.20 | Current: $148.30 | P&L: +$26.35
  ...

📝 DETAILED TRADES
1. BUY NVDA @ $145.20 = $1000.00
2. SELL TSLA @ $238.50 = $1144.80 | P&L: +$144.80 (+14.5%)
...
======================================================================
```

## Commands Reference

```bash
# Setup (first time)
python train_models.py          # Train models
python test_automation.py       # Verify setup

# Control
./start_automation.sh           # Start automation
./stop_automation.sh            # Stop automation
./view_status.sh                # Check status

# Monitoring
tail -f logs/automation.log     # Watch logs
cat data/daily_digest.txt       # View digest
cat data/automation_positions.json | python -m json.tool  # View positions

# Debug
./run_automation_foreground.sh  # Run in foreground
cat logs/automation.error.log   # View errors
```

## Safety Notes

1. **Paper Trading**: Currently simulated (logs trades, doesn't execute real orders)
2. **Position Limits**: Max $3,000 per stock
3. **Market Hours Only**: 9 AM - 3 PM CST, weekdays only
4. **Auto-restart**: Restarts automatically on system reboot

## Next Steps

To connect to real broker:

1. Choose broker API (Alpaca recommended for beginners)
2. Install: `pip install alpaca-trade-api`
3. Edit `execute_trade()` in `automation_scheduler.py`
4. Add broker credentials to `.env`

## Need Help?

- **Setup issues**: See `SETUP_INSTRUCTIONS.md`
- **Detailed docs**: See `AUTOMATION_README.md`
- **Architecture**: See `AUTOMATION_SUMMARY.md`
- **Check logs**: `logs/automation.log` and `logs/automation.error.log`

---

**Ready?** Run these 3 commands:

```bash
python train_models.py          # 1. Train models (first time)
python test_automation.py       # 2. Test setup
./start_automation.sh           # 3. Start automation
```

Then monitor with `./view_status.sh` or `tail -f logs/automation.log`
