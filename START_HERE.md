# 🚀 START HERE - Day Trading Automation

## ✅ Setup Complete!

All automation components are installed and ready to use in this worktree directory:
```
/Users/shashi/.claude-worktrees/sentiment-agent/pensive-easley
```

## 📍 Important: You're Working in a Git Worktree

This is a separate working directory from your main repo. To navigate here from anywhere:

```bash
# From main repo
cd ~/.claude-worktrees/sentiment-agent/pensive-easley

# Or use the helper script from main repo
source ~/sentiment-agent/goto_automation.sh
```

## 🎯 Quick Start (You're Ready!)

All tests passed! You can start immediately:

### Option 1: Start as Background Service (Recommended)

```bash
./start_automation.sh
```

The automation will run continuously in the background.

### Option 2: Test in Foreground First

```bash
./run_automation_foreground.sh
```

This runs in foreground so you can see what's happening. Press Ctrl+C to stop.

## 📊 Check Status

```bash
./view_status.sh
```

Shows:
- Service status
- Today's watchlist (after 8:30 AM)
- Active positions
- Recent trades
- Latest digest (after 3:00 PM)

## 📅 Daily Schedule

The automation runs automatically on weekdays:

| Time | What Happens |
|------|-------------|
| 8:30 AM CST | Generates signals from S&P 500, selects top 10 stocks |
| 9:00 AM CST | Starts trading automation |
| 9:05, 9:10... | Trading cycles every 5 minutes |
| 3:00 PM CST | Market close, generates daily digest |

## 💵 Trading Logic (Your Requirements)

- **First BUY signal**: Invest $1,000
- **Subsequent BUY signals**: Add $250 (max $3,000 per stock)
- **SELL signal**: Close entire position, realize P&L
- **Positions persist** until SELL signal is received

## 📁 Where Things Are

### Control Scripts
```bash
./start_automation.sh           # Start automation
./stop_automation.sh            # Stop automation
./view_status.sh                # Check status
./run_automation_foreground.sh  # Run in foreground
```

### Data Files (in data/)
```bash
data/automation_watchlist.json  # Top 10 stocks for today
data/automation_positions.json  # Current open positions
data/automation_trades.json     # Today's executed trades
data/daily_digest.txt          # End-of-day summary
```

### Logs (in logs/)
```bash
logs/automation.log            # Standard output
logs/automation.error.log      # Errors
```

### Models (in models/)
```bash
models/clf_lgbm_08.pkl        # Classification model
models/reg_q90_08.pkl         # Regression model
```

## 🔍 Monitoring Commands

```bash
# Watch logs in real-time
tail -f logs/automation.log

# Check if service is running
launchctl list | grep daytrading

# View today's watchlist
cat data/automation_watchlist.json | python -m json.tool

# View active positions
cat data/automation_positions.json | python -m json.tool

# View today's trades
cat data/automation_trades.json | python -m json.tool

# View full digest
cat data/daily_digest.txt
```

## 🛠️ Common Commands

```bash
# Stop and restart
./stop_automation.sh && ./start_automation.sh

# Check status
./view_status.sh

# View last 20 log lines
tail -n 20 logs/automation.log

# Follow errors
tail -f logs/automation.error.log
```

## 📚 Documentation

- **START_HERE.md** (this file) - Quick reference
- **AUTOMATION_QUICKSTART.md** - Quick start guide
- **AUTOMATION_README.md** - Detailed documentation
- **AUTOMATION_SUMMARY.md** - Complete architecture
- **SETUP_INSTRUCTIONS.md** - Setup guide

## ⚙️ Configuration

To adjust trading amounts, edit `automation_scheduler.py`:

```python
INITIAL_INVESTMENT = 1000      # First buy
SUBSEQUENT_INVESTMENT = 250    # Additional buys
MAX_POSITION_SIZE = 3000       # Max per stock
```

## 🔄 Example Workflow

```bash
# 1. Start automation (runs in background)
./start_automation.sh

# 2. Wait for 8:30 AM CST for signal generation
# ... automation runs automatically ...

# 3. Check status anytime
./view_status.sh

# 4. View logs
tail -f logs/automation.log

# 5. At 3:00 PM, view digest
cat data/daily_digest.txt

# 6. Tomorrow it runs automatically again!
```

## 🛑 Stopping

```bash
./stop_automation.sh
```

The automation will stop gracefully.

## 🔁 Auto-Restart

The automation is configured to restart automatically on system reboot.

## ⚠️ Important Notes

1. **Paper Trading**: Currently simulated (logs trades, no real execution)
2. **Weekdays Only**: Automatically skips weekends
3. **Market Hours**: Only trades 9 AM - 3 PM CST
4. **Position Limits**: Max $3,000 per stock
5. **Models**: Already trained and copied from main repo

## 🚦 Status Check

Run this right now to see current status:

```bash
./view_status.sh
```

## 🎉 You're Ready!

Everything is set up and tested. To start:

```bash
./start_automation.sh
```

Then monitor with:

```bash
tail -f logs/automation.log
```

Or check status anytime:

```bash
./view_status.sh
```

---

**Next Steps**:
- Start the automation: `./start_automation.sh`
- Let it run until 8:30 AM CST to see signal generation
- At 9:00 AM CST, trading will begin automatically
- At 3:00 PM CST, check the digest: `cat data/daily_digest.txt`

**Questions?** Check the other documentation files or review the logs!
