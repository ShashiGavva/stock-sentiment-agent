# Day Trading Automation System

Automated day trading system that generates signals, manages positions, and provides daily digests.

## Overview

This automation system runs on a schedule to:

1. **8:30 AM CST** - Generate daily signals and populate watchlist with top 10 stocks
2. **9:00 AM CST** - Start day trading automation
3. **Every 5 minutes (9:00 AM - 3:00 PM CST)** - Process trading signals and manage positions
4. **3:00 PM CST** - Generate end-of-day digest and summary

## Trading Logic

The system follows this trading strategy:

- **First BUY signal**: Invest $1,000
- **Subsequent BUY signals**: Add $250 to position (max $3,000 per stock)
- **SELL signal**: Close entire position and realize P&L
- **Positions persist** across 5-minute cycles until a SELL signal is received

## Files Created

### Core Files
- `automation_scheduler.py` - Main scheduler script with all automation logic
- `com.daytrading.automation.plist` - macOS launchd service configuration

### Helper Scripts
- `start_automation.sh` - Start automation as background service
- `stop_automation.sh` - Stop automation service
- `run_automation_foreground.sh` - Run in foreground for testing/debugging

### Data Files (created automatically in `data/` directory)
- `automation_watchlist.json` - Top 10 stocks for the day
- `automation_positions.json` - Currently open positions
- `automation_trades.json` - Trades executed today
- `daily_digest.txt` - End-of-day summary report

### Log Files (created in `logs/` directory)
- `automation.log` - Standard output logs
- `automation.error.log` - Error logs

## Quick Start

### Option 1: Background Service (Recommended for Production)

Start the automation as a background service that will run continuously:

```bash
./start_automation.sh
```

Check status:
```bash
launchctl list | grep daytrading
```

View logs:
```bash
tail -f logs/automation.log
```

Stop the service:
```bash
./stop_automation.sh
```

### Option 2: Foreground (For Testing/Debugging)

Run in foreground to see output directly:

```bash
./run_automation_foreground.sh
```

Press `Ctrl+C` to stop.

## Schedule Details

The automation runs only on **weekdays** (Monday-Friday):

| Time | Task | Description |
|------|------|-------------|
| 8:30 AM CST | Signal Generation | Scans S&P 500, generates signals, selects top 10 for watchlist |
| 9:00 AM CST | Trading Start | Initial trading cycle begins |
| 9:05 AM CST | Trading Cycle | Process signals, manage positions |
| 9:10 AM CST | Trading Cycle | Process signals, manage positions |
| ... | ... | ... (every 5 minutes) |
| 2:55 PM CST | Trading Cycle | Final trading cycle |
| 3:00 PM CST | Market Close | Generate digest, summarize day's performance |

## Manual Testing

You can run individual components for testing:

```bash
# Activate virtual environment
source .venv312/bin/activate

# Edit automation_scheduler.py and uncomment at the bottom:
# generate_daily_signals()    # Test signal generation
# process_trading_cycle()     # Test single trading cycle
# generate_digest()           # Test digest generation

python automation_scheduler.py
```

## Configuration

Edit `automation_scheduler.py` to adjust:

```python
INITIAL_INVESTMENT = 1000      # First buy amount
SUBSEQUENT_INVESTMENT = 250    # Additional buy amount
MAX_POSITION_SIZE = 3000       # Maximum per position
```

## Email Notifications (TODO)

To enable email digest delivery, configure SMTP settings in the `send_email_digest()` function:

```python
def send_email_digest(digest_text):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    sender_password = "your-app-password"
    recipient_email = "recipient@email.com"
    # ... implementation
```

## Monitoring

### View Real-Time Logs
```bash
# Standard output
tail -f logs/automation.log

# Errors
tail -f logs/automation.error.log
```

### Check Today's Performance
```bash
cat data/daily_digest.txt
```

### View Active Positions
```bash
cat data/automation_positions.json | python -m json.tool
```

### View Today's Trades
```bash
cat data/automation_trades.json | python -m json.tool
```

## Troubleshooting

### Automation Not Starting
```bash
# Check if service is loaded
launchctl list | grep daytrading

# Check error logs
cat logs/automation.error.log

# Restart the service
./stop_automation.sh
./start_automation.sh
```

### No Signals Generated
- Verify models exist: `ls -la models/clf_lgbm_08.pkl models/reg_q90_08.pkl`
- Check signal generation logs
- Manually test: `python daily_signals.py`

### Trades Not Executing
- Verify watchlist exists: `cat data/automation_watchlist.json`
- Check market hours (9 AM - 3 PM CST on weekdays)
- Review trading cycle logs for errors

### System Reboot
The automation will automatically restart on system reboot due to `RunAtLoad` in the plist configuration.

## Architecture

```
automation_scheduler.py
├── Signal Generation (8:30 AM)
│   ├── Load ML models
│   ├── Scan S&P 500 stocks
│   ├── Generate predictions
│   └── Save top 10 to watchlist
│
├── Trading Cycles (9:00 AM - 3:00 PM, every 5 min)
│   ├── Load watchlist
│   ├── For each stock:
│   │   ├── Get intraday data
│   │   ├── Generate signals
│   │   ├── Check position status
│   │   ├── Execute trades (BUY/SELL)
│   │   └── Update positions
│   └── Save positions & trades
│
└── End-of-Day Digest (3:00 PM)
    ├── Load all trades
    ├── Calculate P&L metrics
    ├── Generate report
    └── (Optional) Send email
```

## Safety Notes

1. **Paper Trading**: This system currently logs trades but doesn't execute real orders
2. **Position Limits**: Max $3,000 per stock to manage risk
3. **Weekday Only**: Automatically skips weekends
4. **Market Hours**: Only trades during market hours (9 AM - 3 PM CST)

## Next Steps

To integrate with real broker API:

1. Choose broker (Interactive Brokers, Alpaca, TD Ameritrade, etc.)
2. Install broker SDK: `pip install alpaca-trade-api` (example)
3. Modify `execute_trade()` function to place real orders
4. Add authentication and API credentials
5. Implement additional error handling and position reconciliation

## Support

For issues or questions:
- Check logs: `logs/automation.log` and `logs/automation.error.log`
- Review data files in `data/` directory
- Test individual components manually
