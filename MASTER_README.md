# Day Trading Automation System - Complete Guide

## 🎯 What You Have

A complete, professional day trading automation system with **web-based control panel** for manual control.

## 🚀 Quick Start (2 Steps)

### Step 1: Start the Control Panel

```bash
cd ~/.claude-worktrees/sentiment-agent/pensive-easley
./start_automation_ui.sh
```

### Step 2: Open Browser

Go to: **http://localhost:5002**

That's it! Everything is controlled through the beautiful web interface.

## 📊 Web Control Panel Features

### Real-Time Dashboard
- Live P&L tracking (updates every 3 seconds)
- Open positions with current prices
- Trade counter and activity log
- Performance metrics (win rate, total trades, etc.)

### Manual Controls
- **Generate Signals**: Scan S&P 500 and pick top 10 stocks (anytime)
- **Start Trading**: Begin automated trading every 5 minutes
- **Stop Trading**: Pause automation without closing positions
- **Retrain Models**: Retrain ML models with ALL historical data
- **View Digest**: See comprehensive daily summary
- **Send Email**: Email digest to any address

### What Makes It Special
- ✅ **No command line needed** - everything via web UI
- ✅ **Real-time updates** - see changes instantly
- ✅ **Visual progress** - progress bars and status indicators
- ✅ **Mobile friendly** - works on phone/tablet
- ✅ **Color-coded P&L** - green for profit, red for loss
- ✅ **One-click actions** - generate signals, start trading, etc.

## 📁 Files Overview

### Web Interface
- **`automation_ui.py`** - Web server with API endpoints
- **`templates/automation_control.html`** - Beautiful control panel UI
- **`start_automation_ui.sh`** - One-click UI startup

### Documentation
- **`UI_QUICKSTART.md`** - Start here! Quick 2-minute guide
- **`AUTOMATION_UI_GUIDE.md`** - Complete UI user manual
- **`AUTOMATION_SUMMARY.md`** - System architecture
- **`START_HERE.md`** - General automation overview

### Core System (runs via UI)
- **`automation_scheduler.py`** - Background automation engine
- **`daily_signals.py`** - Signal generation
- **`app.py`** - Original Flask app (still works)
- **`train_models.py`** - ML model training

### Helper Scripts
- **`start_automation_ui.sh`** - Start web control panel
- **`view_status.sh`** - Command-line status viewer
- **`test_automation.py`** - Test setup

## 🎮 Using the Control Panel

### Morning Routine

1. **Start UI** (8:00 AM)
   ```bash
   ./start_automation_ui.sh
   ```
   Open: http://localhost:5002

2. **Generate Signals** (8:30 AM or anytime)
   - Click "Generate Signals" button
   - Wait 5-10 minutes
   - Top 10 stocks appear in watchlist

3. **Start Trading** (9:00 AM)
   - Click "Start Trading" button
   - Automation runs every 5 minutes
   - Dashboard updates in real-time

### During Market Hours

- Monitor dashboard (auto-updates every 3 seconds)
- Watch positions and P&L
- Optional: Stop/restart trading if needed

### End of Day (3:00 PM)

1. **Stop Trading**
   - Click "Stop Trading" button

2. **View Performance**
   - Click "View Digest" button
   - Review day's trades and P&L

3. **Send Email**
   - Enter email: `shashi.gavva@gmail.com`
   - Click "Send Email"
   - Check your inbox

4. **Retrain Models** ⭐ **Important!**
   - Click "Retrain Models" button
   - Wait 10-30 minutes
   - Models use ALL historical data (not just today)
   - Better predictions for tomorrow

## 💰 Trading Logic (Automated)

The system follows your exact requirements:

1. **First BUY signal**: Invest **$1,000**
2. **Subsequent BUY signals**: Add **$250** (max $3,000/stock)
3. **SELL signal**: Close entire position, realize P&L
4. **Positions persist** until SELL signal received

## 🤖 ML Model Retraining

**Critical Feature**: End-of-day model retraining

### How It Works
- Click "Retrain Models" in UI
- System loads ALL historical data (not just current day)
- Trains LightGBM models on complete dataset
- Saves new models for tomorrow's signals
- Takes 10-30 minutes

### When to Use
- **Daily** (recommended): Retrain at end of each trading day
- **Weekly**: Minimum once per week
- **After major market events**: Captures new patterns
- **When performance degrades**: Refresh with latest data

### What It Does
1. Loads complete training dataset
2. Trains classification model (8% target)
3. Trains regression model (Q90 predictions)
4. Saves to `models/clf_lgbm_08.pkl` and `models/reg_q90_08.pkl`
5. Next signal generation uses new models

## 📧 Email Digest

Already configured and ready to use!

**Email Settings** (from `.env`):
- From: thestockwatchapp@gmail.com
- To: shashi.gavva@gmail.com

**To Send**:
1. Click "View Digest" (optional - to preview)
2. Enter email address (or keep default)
3. Click "Send Email"
4. Check inbox!

**Digest Includes**:
- Today's watchlist (top 10 stocks)
- Total signals generated
- Trading activity (buys, sells, total trades)
- Performance (total P&L, win rate)
- Open positions with unrealized P&L
- Detailed trade log

## 🎨 UI Screenshots (What You'll See)

### Dashboard Layout
```
┌─────────────────────────────────────────────────┐
│  Day Trading Automation Control Panel           │
├─────────────────────────────────────────────────┤
│                                                 │
│  📊 Today's Performance    📈 Trading Activity  │
│  ┌─────────────────┐      ┌──────────────────┐ │
│  │ Total P&L       │      │ Total Trades: 15 │ │
│  │   $342.50 🟢    │      │ Buys: 10         │ │
│  │                 │      │ Sells: 5         │ │
│  └─────────────────┘      └──────────────────┘ │
│                                                 │
│  🔍 Signal Gen         💹 Day Trading          │
│  ┌─────────────────┐      ┌──────────────────┐ │
│  │ Status: Complete│      │ Status: Running  │ │
│  │ [Generate]      │      │ [Stop Trading]   │ │
│  └─────────────────┘      └──────────────────┘ │
│                                                 │
│  📋 Today's Watchlist                          │
│  ┌─────────────────────────────────────────┐  │
│  │ AAPL  MSFT  NVDA  TSLA  AMD  GOOGL  ... │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  💼 Open Positions                             │
│  ┌─────────────────────────────────────────┐  │
│  │ NVDA: 8.5 shares @ $145.20              │  │
│  │ Current: $148.30 | P&L: +$26.35 (1.8%) │  │
│  └─────────────────────────────────────────┘  │
│                                                 │
│  📧 Daily Digest & Email                       │
│  ┌─────────────────────────────────────────┐  │
│  │ [View Digest] [Send Email]              │  │
│  └─────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

## 📱 Access from Phone/Tablet

1. Find your computer's IP:
   ```bash
   ifconfig | grep "inet " | grep -v 127.0.0.1
   ```

2. Open on mobile:
   ```
   http://YOUR_IP:5002
   ```

3. Full functionality on mobile!

## 🔧 Two Ways to Use the System

### Option 1: Web Control Panel (Recommended) ⭐

**Best for**: Manual control, testing, missed schedules

```bash
./start_automation_ui.sh
# Open browser, click buttons
```

**Advantages**:
- Visual interface
- Start/stop anytime
- Real-time monitoring
- Manual signal generation (if you missed 8:30 AM)
- On-demand model retraining

### Option 2: Scheduled Automation (Advanced)

**Best for**: Fully hands-off, daily automation

```bash
./start_automation.sh
# Runs on schedule automatically
```

**Schedule**:
- 8:30 AM CST - Generate signals
- 9:00 AM CST - Start trading
- Every 5 min - Trading cycles
- 3:00 PM CST - Generate digest

**Note**: Can use both! Run scheduled automation AND open UI to monitor.

## 🎯 Your Specific Requirements ✅

All implemented and working:

### ✅ Manual Control via UI
- Generate signals anytime (not just 8:30 AM)
- Start/stop trading anytime (not just 9:00 AM)
- Everything controlled through web interface

### ✅ Real-Time Monitoring
- Stocks picked for the day (watchlist)
- How much invested in each stock (per position)
- How much profit made (realized + unrealized P&L)
- Current trading status and activity

### ✅ ML Training
- Retrain models at end of each day
- Uses ALL historical data (not just current day)
- One-click via "Retrain Models" button
- Takes 10-30 minutes, runs in background

### ✅ Email Digest
- Comprehensive daily summary
- Send to any email address
- Already configured with your credentials
- Includes all trades, positions, and P&L

## 🎓 Learning the UI

**Total time to learn**: 5 minutes

1. **Open UI**: `./start_automation_ui.sh` → http://localhost:5002
2. **Look at dashboard**: Everything is labeled clearly
3. **Try buttons**: All have confirmation popups (safe to explore)
4. **Watch updates**: Dashboard refreshes automatically
5. **Done!** You now know everything

## 📊 Data Storage

All data in `data/` directory:

| File | Purpose |
|------|---------|
| `automation_watchlist.json` | Top 10 stocks |
| `automation_positions.json` | Open positions |
| `automation_trades.json` | Today's trades |
| `daily_digest.txt` | Daily summary |

View anytime:
```bash
cat data/automation_positions.json | python -m json.tool
```

## 🆘 Troubleshooting

### UI Won't Start

```bash
# Check port 5002
lsof -i :5002

# If occupied, kill it
kill -9 <PID>

# Restart
./start_automation_ui.sh
```

### Can't Generate Signals

- **Check models exist**: `ls models/*.pkl`
- **Check internet** (needs to fetch stock data)
- **Wait for completion** (takes 5-10 minutes)

### Trading Won't Start

- **Generate signals first** (need watchlist)
- **Check market hours** (9 AM - 3 PM CST, weekdays)

### Email Not Sending

- **Check .env file**: `cat .env | grep SMTP`
- Credentials already configured for you!

## 📚 Documentation Map

1. **Start Here**: `UI_QUICKSTART.md` (2 minutes)
2. **Learn UI**: `AUTOMATION_UI_GUIDE.md` (detailed guide)
3. **Understand System**: `AUTOMATION_SUMMARY.md` (architecture)
4. **Command Line**: `START_HERE.md` (if you prefer CLI)

## 🎉 Summary

You now have:

✅ **Web-based control panel** - Everything via beautiful UI
✅ **Real-time monitoring** - See P&L, positions, trades live
✅ **Manual controls** - Start/stop anything, anytime
✅ **ML retraining** - One-click training with ALL data
✅ **Email digests** - Daily summary to your inbox
✅ **Mobile friendly** - Monitor from anywhere
✅ **Zero command line** - Everything via browser (except startup)

## 🚀 Get Started Now!

```bash
cd ~/.claude-worktrees/sentiment-agent/pensive-easley
./start_automation_ui.sh
```

Open: **http://localhost:5002**

**That's it!** Start trading with clicks, not code.

---

**Questions?**
- Check `UI_QUICKSTART.md` for quick answers
- Check `AUTOMATION_UI_GUIDE.md` for detailed help
- Check terminal output for logs
