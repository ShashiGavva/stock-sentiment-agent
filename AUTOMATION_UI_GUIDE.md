# Automation Control Panel - User Guide

## Overview

The Automation Control Panel is a web-based interface that gives you complete control over the day trading automation system. You can manually trigger signal generation, start/stop trading, retrain ML models, view real-time performance, and send daily digests via email.

## Starting the Control Panel

```bash
cd ~/.claude-worktrees/sentiment-agent/pensive-easley
./start_automation_ui.sh
```

Then open in your browser: **http://localhost:5002**

## Features

### 📊 Real-Time Dashboard

The dashboard auto-refreshes every 3 seconds and shows:

#### Today's Performance
- **Total P&L**: Combined realized + unrealized profit/loss
- **Realized P&L**: Profit/loss from closed positions
- **Unrealized P&L**: Current profit/loss from open positions
- **Total Invested**: Total capital deployed today

#### Trading Activity
- **Total Trades**: Number of buy + sell orders
- **Buy Orders**: Count of buy executions
- **Sell Orders**: Count of sell executions
- **Trading Cycles**: Number of 5-minute cycles completed

### 🔍 Signal Generation Control

**Purpose**: Scan S&P 500 stocks and select top 10 for day trading

**When to Use**:
- Before market open (8:30 AM CST or earlier)
- Anytime you want fresh signals
- If you missed the scheduled generation

**How to Use**:
1. Click **"Generate Signals"** button
2. Confirmation popup appears (generation takes 5-10 minutes)
3. Progress bar shows scan progress
4. When complete, watchlist updates with top 10 stocks

**Status Indicators**:
- 🟢 **Running**: Currently scanning stocks (pulsing animation)
- 🔵 **Complete**: Signal generation finished
- ⚪ **Idle**: Not running
- 🔴 **Error**: Something went wrong (check error message)

### 💹 Day Trading Automation Control

**Purpose**: Execute trading logic every 5 minutes

**Trading Logic**:
- First BUY signal: Invest $1,000
- Subsequent BUY signals: Add $250 (max $3,000 per stock)
- SELL signal: Close entire position

**How to Use**:

**Start Trading**:
1. Ensure signals are generated (watchlist populated)
2. Click **"Start Trading"** button
3. Confirmation popup appears
4. Trading begins immediately and runs every 5 minutes
5. Button becomes disabled, **"Stop Trading"** becomes active

**Stop Trading**:
1. Click **"Stop Trading"** button
2. Confirmation popup appears
3. Current cycle completes, then trading stops
4. Positions remain open (not automatically closed)

**Status Indicators**:
- 🟢 **Running**: Trading automation active
- 🟠 **Stopped**: Trading automation stopped
- ⚪ **Idle**: Not started
- 🔴 **Error**: Error occurred

**Important Notes**:
- Trading runs continuously every 5 minutes once started
- You can stop anytime without losing positions
- Positions persist until SELL signal or manual intervention
- Stopping does NOT close positions automatically

### 🤖 ML Model Training

**Purpose**: Retrain classification and regression models with all historical data

**When to Use**:
- End of each trading day (automatically captures new data)
- After significant market events
- When model performance degrades
- Manual retraining as needed

**How to Use**:
1. Click **"Retrain Models"** button
2. Confirmation popup appears (training takes 10-30 minutes)
3. Progress bar shows training progress
4. When complete, new models are saved and used for next signal generation

**What It Does**:
- Loads ALL historical trading data (not just current day)
- Trains LightGBM classification model (8% target)
- Trains LightGBM regression model (Q90 predictions)
- Saves models to `models/clf_lgbm_08.pkl` and `models/reg_q90_08.pkl`
- Future signal generation uses new models

**Status Indicators**:
- 🟢 **Running**: Training in progress
- 🔵 **Complete**: Training finished successfully
- ⚪ **Idle**: Not running
- 🔴 **Error**: Training failed

### 📋 Today's Watchlist

Shows the top 10 stocks selected for day trading:
- Updates when signal generation completes
- Shows total signals generated
- Displays generation timestamp
- Each stock shown as a colored badge

### 💼 Open Positions

Real-time view of all active positions:

**For Each Position**:
- **Symbol**: Stock ticker
- **Shares**: Number of shares owned
- **Entry Price**: Average purchase price
- **Current Price**: Latest market price (refreshes every 3 seconds)
- **Invested**: Total capital invested
- **Current Value**: Current market value
- **Unrealized P&L**: Current profit/loss ($ and %)
- **Entry Time**: When position was opened

**Color Coding**:
- 🟢 Green: Profitable position (positive P&L)
- 🔴 Red: Losing position (negative P&L)

### 📧 Daily Digest & Email

**View Digest**:
1. Click **"View Digest"** button
2. Digest appears below button showing:
   - Today's watchlist
   - Trading activity summary
   - Performance metrics
   - Open positions with unrealized P&L
   - Detailed trade log
3. Click again to hide

**Send Email**:
1. Enter email address in input field
2. Click **"Send Email"** button
3. Digest is generated and sent via email
4. Success/error message appears
5. Email contains full text digest

**Email Configuration**:
Email settings are configured in `.env` file:
```
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=thestockwatchapp@gmail.com
SMTP_PASSWORD=rwvsjvvxxqqzcryd
```

**Default Recipients** (from .env):
- shashi.gavva@gmail.com
- thestockwatchapp@gmail.com

You can send to any email address using the web UI.

## Typical Daily Workflow

### Morning (8:00 AM - 9:00 AM CST)

1. **Start Control Panel**
   ```bash
   ./start_automation_ui.sh
   ```

2. **Generate Signals** (8:30 AM or earlier)
   - Click "Generate Signals"
   - Wait 5-10 minutes for completion
   - Review top 10 watchlist

3. **Start Trading** (9:00 AM)
   - Click "Start Trading"
   - Trading begins immediately
   - Runs automatically every 5 minutes

### During Market Hours (9:00 AM - 3:00 PM CST)

- **Monitor Dashboard**: Auto-refreshes every 3 seconds
- **Check Positions**: View real-time P&L
- **Optional**: Stop/restart trading if needed

### End of Day (3:00 PM CST)

1. **Stop Trading**
   - Click "Stop Trading"
   - Review final positions

2. **View Digest**
   - Click "View Digest"
   - Review day's performance

3. **Send Email**
   - Enter email (or use default)
   - Click "Send Email"
   - Check your inbox

4. **Retrain Models** (Optional but Recommended)
   - Click "Retrain Models"
   - Training uses all historical data including today
   - Wait 10-30 minutes
   - Models ready for tomorrow

### Late Evening (Optional)

- Review next day's trading plan
- Check email digest
- Prepare for tomorrow

## Keyboard Shortcuts

None currently - all controls via buttons.

## Browser Requirements

- Modern browser (Chrome, Firefox, Safari, Edge)
- JavaScript enabled
- Recommended: Keep tab active for real-time updates
- Works on mobile browsers (responsive design)

## Troubleshooting

### Control Panel Won't Start

```bash
# Check if port 5002 is already in use
lsof -i :5002

# Kill existing process if found
kill -9 <PID>

# Restart
./start_automation_ui.sh
```

### Signal Generation Fails

- **Check models exist**: `ls -lh models/*.pkl`
- **Check internet connection** (needs to fetch stock data)
- **Check error message** in UI
- **View logs**: Check terminal output

### Trading Won't Start

- **Ensure watchlist is loaded** (generate signals first)
- **Check market hours** (9 AM - 3 PM CST, weekdays)
- **Check error message** in UI

### Email Not Sending

- **Check .env file** has valid credentials
- **Check email address** is valid
- **Check SMTP server** is accessible
- **Check error message** in UI
- **Verify .env variables**:
  ```bash
  cat .env | grep SMTP
  ```

### Dashboard Not Updating

- **Check JavaScript console** (F12 in browser)
- **Refresh page** (Ctrl+R or Cmd+R)
- **Check network tab** for failed requests
- **Verify backend is running** (check terminal)

### Positions Not Showing

- **Ensure trading has started**
- **Wait for first trading cycle** (up to 5 minutes)
- **Check data files**:
  ```bash
  cat data/automation_positions.json
  ```

## Data Files

All data stored in `data/` directory:

| File | Purpose | Updated |
|------|---------|---------|
| `automation_watchlist.json` | Top 10 stocks | Signal generation |
| `automation_positions.json` | Open positions | Every 5 min |
| `automation_trades.json` | Today's trades | Every 5 min |
| `daily_digest.txt` | Daily summary | On demand |

## API Endpoints

If you want to integrate with other tools:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/automation/status` | GET | Get full status |
| `/api/automation/generate-signals` | POST | Trigger signal generation |
| `/api/automation/start-trading` | POST | Start trading |
| `/api/automation/stop-trading` | POST | Stop trading |
| `/api/automation/retrain` | POST | Trigger ML training |
| `/api/automation/digest` | GET | Get digest text |
| `/api/automation/send-email` | POST | Send email digest |

Example:
```bash
# Get status
curl http://localhost:5002/api/automation/status

# Start trading
curl -X POST http://localhost:5002/api/automation/start-trading
```

## Safety Features

1. **Confirmation Popups**: All major actions require confirmation
2. **Real-time Status**: See exactly what's happening
3. **Error Messages**: Clear error reporting
4. **Position Tracking**: Never lose track of open positions
5. **Paper Trading**: Currently simulated (not real execution)

## Customization

### Change Trading Amounts

Edit `automation_ui.py`:
```python
INITIAL_INVESTMENT = 1000      # Change first buy amount
SUBSEQUENT_INVESTMENT = 250    # Change additional buy amount
MAX_POSITION_SIZE = 3000       # Change max per stock
```

### Change Refresh Rate

Edit `automation_control.html` at bottom:
```javascript
refreshInterval = setInterval(updateStatus, 3000); // Change 3000 to desired ms
```

### Change Port

Edit `automation_ui.py` at bottom:
```python
app.run(debug=True, host='0.0.0.0', port=5002)  # Change 5002 to desired port
```

## Advanced Usage

### Running Multiple Days

The control panel can run continuously:
1. Keep browser tab open
2. Leave automation running overnight
3. System handles everything automatically
4. Positions persist across days

### Remote Access

To access from another device on your network:

1. Find your local IP:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Access from other device:
   ```
   http://YOUR_IP:5002
   ```

### Automated Scheduling

Combine with cron/launchd for fully automated operation:
- Auto-start control panel at 8:00 AM
- Auto-generate signals at 8:30 AM
- Auto-start trading at 9:00 AM
- Auto-stop trading at 3:00 PM
- Auto-send digest at 3:05 PM
- Auto-retrain models at 4:00 PM

(See `automation_scheduler.py` for scheduled version)

## Getting Help

- **Check terminal output** for detailed logs
- **Check browser console** (F12) for JavaScript errors
- **Review data files** in `data/` directory
- **Check this guide** for common solutions
- **Review API responses** for error details

## Summary

The Automation Control Panel gives you complete manual control over the day trading system. Use it to:
- ✅ Generate signals on demand
- ✅ Start/stop trading anytime
- ✅ Monitor real-time performance
- ✅ Track all positions and P&L
- ✅ Retrain models with new data
- ✅ Send daily digest emails

**Quick Start**: `./start_automation_ui.sh` → Open http://localhost:5002 → Click buttons!
