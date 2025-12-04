# Automation Control Panel - Quick Start

## 🚀 Start the UI (1 command)

```bash
cd ~/.claude-worktrees/sentiment-agent/pensive-easley
./start_automation_ui.sh
```

Then open: **http://localhost:5002**

## 📊 What You'll See

A beautiful dashboard with:
- 📈 Real-time performance (P&L, trades, positions)
- 🎛️ Control buttons (generate signals, start/stop trading)
- 💼 Live position tracking with current prices
- 📧 Email digest functionality
- 🤖 ML model retraining

## ⚡ Quick Actions

### 1. Generate Today's Signals (If You Missed 8:30 AM)

Click: **"Generate Signals"** button

- Takes 5-10 minutes
- Scans S&P 500 stocks
- Selects top 10 for watchlist
- Progress bar shows status

### 2. Start Trading

Click: **"Start Trading"** button

- Trades every 5 minutes automatically
- First BUY: $1,000
- Additional BUYs: $250
- SELL: Close entire position
- Runs until you stop it

### 3. Monitor Performance

Dashboard auto-updates every 3 seconds:
- Total P&L (realized + unrealized)
- Open positions with live prices
- Trade count and activity
- Win/loss tracking

### 4. Stop Trading

Click: **"Stop Trading"** button

- Stops after current cycle
- Positions remain open
- Can restart anytime

### 5. View Daily Digest

Click: **"View Digest"** button

- See full day summary
- All trades listed
- Performance metrics
- Open positions

### 6. Send Email Digest

1. Enter email address (or use thestockwatchapp@gmail.com)
2. Click: **"Send Email"**
3. Check your inbox

### 7. Retrain Models (End of Day)

Click: **"Retrain Models"** button

- Uses ALL historical data (not just today)
- Takes 10-30 minutes
- New models ready for tomorrow
- Recommended at end of each trading day

## 🎨 UI Features

### Status Badges

- 🟢 **Running** (pulsing): Action in progress
- 🔵 **Complete**: Action finished
- ⚪ **Idle**: Not running
- 🔴 **Error**: Something wrong
- 🟠 **Stopped**: Manually stopped

### Color-Coded P&L

- 🟢 **Green numbers**: Profitable
- 🔴 **Red numbers**: Losing

### Progress Bars

Show real-time progress for:
- Signal generation (stock by stock)
- ML model training (progress percentage)

## 📋 Typical Day

### Morning (8:00 AM)

```bash
# 1. Start UI
./start_automation_ui.sh
```

### 8:30 AM (or whenever you're ready)

1. Open http://localhost:5002
2. Click "Generate Signals"
3. Wait for top 10 watchlist

### 9:00 AM (Market Open)

1. Click "Start Trading"
2. Automation runs every 5 minutes
3. Monitor dashboard

### During Day

- Dashboard updates automatically
- Check positions anytime
- Watch P&L grow (hopefully! 🚀)

### 3:00 PM (Market Close)

1. Click "Stop Trading"
2. Click "View Digest"
3. Enter email and click "Send Email"
4. Click "Retrain Models" (recommended!)

## 🔧 Troubleshooting

**UI won't start?**
```bash
# Check if already running
lsof -i :5002

# Or just try a different terminal
./start_automation_ui.sh
```

**No watchlist?**
- Click "Generate Signals" first
- Wait for it to complete

**Trading won't start?**
- Generate signals first (need watchlist)
- Check it's weekday market hours

**Email not sending?**
- Check .env file exists and has credentials
- Already configured for you!

## 💡 Tips

1. **Keep browser tab active** for real-time updates
2. **Generate signals before 9 AM** for best results
3. **Let trading run continuously** don't stop/start frequently
4. **Retrain models daily** to improve predictions
5. **Check email digest** to track progress
6. **Monitor positions** to learn what works

## 📱 Mobile Friendly

The UI works on mobile browsers too!
- Same URL: http://YOUR_IP:5002
- Fully responsive design
- All features available

## 🎯 One-Line Commands

```bash
# Start UI
./start_automation_ui.sh

# Check status from command line
curl http://localhost:5002/api/automation/status | python -m json.tool

# Trigger signal generation via API
curl -X POST http://localhost:5002/api/automation/generate-signals

# Start trading via API
curl -X POST http://localhost:5002/api/automation/start-trading
```

## 📚 More Info

For detailed documentation, see:
- `AUTOMATION_UI_GUIDE.md` - Complete user guide
- `AUTOMATION_SUMMARY.md` - System architecture
- `START_HERE.md` - General automation info

## 🎉 That's It!

Three steps to automated day trading:
1. `./start_automation_ui.sh`
2. Open browser to http://localhost:5002
3. Click buttons!

**Everything is visual and self-explanatory.** Just explore and click around!

---

**Need Help?** Check the terminal output where you started the UI - all actions are logged there.
