# Tomorrow's Automatic Schedule (Thursday, Dec 5, 2025)

## ✅ Everything Runs Automatically - No Action Needed!

---

## 🌅 8:30 AM CST - Signal Generation

**What happens automatically:**
```
1. Scheduler wakes up
2. Scans all S&P 500 stocks (~500 stocks)
3. ML models predict 10-day returns
4. Selects top 10 highest-probability stocks
5. Saves watchlist to: data/automation_watchlist.json
```

**Duration**: 5-10 minutes

**Log message**: ✅ Signal generation complete

---

## 📈 9:00 AM CST - Day Trading Starts

**What happens automatically:**
```
1. Loads watchlist (top 10 stocks from 8:30 AM)
2. Begins 5-minute trading cycles
3. First trading cycle executes immediately
```

**Log message**: 🚀 Day trading started

---

## 🔄 9:05 AM - 3:00 PM CST - Trading Cycles (Every 5 Minutes)

**Total cycles**: 72 per day

**Each cycle automatically:**
```
1. Fetches latest 1-minute intraday data for watchlist stocks
2. Generates BUY/SELL/HOLD signals
3. Executes trades:
   ├─ BUY signal + no position → Invest $1,000
   ├─ BUY signal + existing position → Add $250 (max $3,000/stock)
   └─ SELL signal → Close entire position
4. Updates: data/automation_positions.json
5. Logs trade: data/automation_trades.json
```

**Example cycle times:**
- 9:05, 9:10, 9:15, 9:20, 9:25, 9:30, 9:35, 9:40, 9:45, 9:50, 9:55
- 10:00, 10:05, 10:10... (continues every 5 minutes)
- 14:00, 14:05, 14:10, 14:15, 14:20, 14:25, 14:30, 14:35, 14:40, 14:45, 14:50, 14:55

**Last cycle**: 2:55 PM CST

---

## 🌆 3:00 PM CST - End of Day Digest

**What happens automatically:**
```
1. Compiles all day's activity
2. Calculates:
   ├─ Realized P&L (closed positions)
   ├─ Unrealized P&L (open positions)
   ├─ Total P&L
   ├─ Win rate
   └─ Trade summary
3. Saves to: data/daily_digest.txt
```

**Log message**: 📧 Daily digest generated

---

## 🖥️ What You Can Do (Optional)

### Monitor in Real-Time
```bash
# Open web UI
./start_automation_ui.sh
# Then visit: http://localhost:5002
```

**Dashboard shows:**
- Real-time P&L updates every 3 seconds
- Open positions with current prices
- Total trades count
- Win/loss tracking

### End of Day Actions (Recommended)

**1. Review Performance**
- Open http://localhost:5002
- Click "View Digest"
- Review day's results

**2. Send Email Digest**
- Enter email: shashi.gavva@gmail.com
- Click "Send Email"
- Check inbox

**3. Retrain ML Models** ⭐ **Important!**
- Click "Retrain Models"
- Wait 10-30 minutes
- Improves predictions for next day
- Uses ALL historical data

---

## 📊 What Gets Created Tomorrow

### Files Generated Automatically

```
data/
├── automation_watchlist.json       # Created at 8:30 AM
│   └── Top 10 stocks with probabilities
│
├── automation_positions.json       # Updated every 5 min (9 AM - 3 PM)
│   └── Current open positions
│
├── automation_trades.json          # Updated on each trade
│   └── All trades executed today
│
├── daily_digest.txt               # Created at 3:00 PM
│   └── Comprehensive daily summary
│
└── daily_signals.csv              # Created at 8:30 AM
    └── All ~500 stocks with predictions

logs/
├── automation.log                 # All activity logs
└── automation.error.log          # Any errors (hopefully empty!)
```

---

## 🔍 How to Verify It's Working Tomorrow

### Option 1: Web UI (Easiest)
```bash
# Morning: Open UI
./start_automation_ui.sh
# Visit: http://localhost:5002

# Watch for:
8:30 AM → Signal Generation status changes to "Running" then "Complete"
9:00 AM → Day Trading status changes to "Running"
Every 5 min → Trade counter increases, positions update
```

### Option 2: Log Files
```bash
# Real-time logs
tail -f logs/automation.log

# You should see:
8:30 AM → "🔍 Generating daily signals..."
8:35 AM → "✅ Signal generation complete. Top 10 saved to watchlist."
9:00 AM → "🚀 Starting day trading automation..."
9:05 AM → "💹 Trading cycle 1/72 complete. Trades: 2, Positions: 2"
...
```

### Option 3: Data Files
```bash
# After 8:30 AM - Check watchlist
cat data/automation_watchlist.json

# After 9:00 AM - Check positions
cat data/automation_positions.json

# After 3:00 PM - Check digest
cat data/daily_digest.txt
```

---

## ⚙️ Current Setup Status

✅ **Automation Service**: Running (PID: 80585)
✅ **Auto-start on boot**: Enabled (RunAtLoad=true)
✅ **Auto-restart**: Enabled (KeepAlive=true)
✅ **ML Models**: Trained and ready (26 features)
✅ **Email Config**: Ready (.env configured)
✅ **Web UI**: Available (http://localhost:5002)

---

## 🚨 What If Something Goes Wrong?

### Automation Not Running
```bash
# Check status
launchctl list | grep daytrading

# If not running, restart
./start_automation.sh
```

### No Signals at 8:30 AM
```bash
# Check logs
tail -f logs/automation.error.log

# Run manually via UI
# 1. Open http://localhost:5002
# 2. Click "Generate Signals"
```

### Trading Not Starting at 9:00 AM
```bash
# Check if watchlist exists
cat data/automation_watchlist.json

# If empty, generate signals manually via UI
```

### Check Overall Status Anytime
```bash
./view_status.sh
```

---

## 📅 Daily Routine (Recommended)

### Morning (8:00-9:00 AM)
1. ☕ Grab coffee
2. Open http://localhost:5002
3. Watch signals generate at 8:30 AM (5-10 min)
4. Review top 10 stocks selected
5. Trading auto-starts at 9:00 AM

### During Day (9:00 AM - 3:00 PM)
- Monitor dashboard occasionally
- Watch P&L grow (hopefully! 📈)
- System trades automatically every 5 minutes
- No action needed

### End of Day (3:00-3:30 PM)
1. Review digest: Click "View Digest"
2. Send to email: Click "Send Email"
3. **Retrain models**: Click "Retrain Models" ⭐
4. Close UI (automation keeps running)

### Weekend
- Automation automatically skips Saturday/Sunday
- Optional: Review week's performance
- Optional: Retrain models with week's data

---

## 💡 Pro Tips

1. **Keep browser tab open** during trading hours for real-time monitoring
2. **Retrain models daily** for best results (uses all historical data)
3. **Check email digest** to track long-term performance
4. **Don't stop/start frequently** - let automation run smoothly
5. **Paper trading first** - Current setup doesn't execute real trades yet
6. **Use mobile access** - Access http://YOUR_IP:5002 from phone

---

## 🎉 Summary

### What's Automatic (No Action Needed)
- ✅ Signal generation at 8:30 AM
- ✅ Trading start at 9:00 AM
- ✅ Trading cycles every 5 minutes
- ✅ Digest generation at 3:00 PM
- ✅ Runs every weekday automatically
- ✅ Skips weekends/holidays

### What's Manual (Your Choice)
- 🔘 Send email digest (via UI)
- 🔘 Retrain ML models (via UI, recommended daily)
- 🔘 Monitor dashboard (via UI)
- 🔘 Override automation (via UI buttons)

---

**Tomorrow morning, sit back and watch it run automatically! Everything is set up and ready.**

The automation will:
1. Wake up at 8:30 AM CST
2. Generate signals
3. Start trading at 9 AM
4. Execute trades every 5 minutes
5. Generate digest at 3 PM

**You're all set! 🚀**
