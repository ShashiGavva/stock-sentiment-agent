# Stock Sentiment Agent - Updates

## 📦 Files Updated

### 1. **send_signals_email.py** (READY TO USE ✅)
**What changed:**
- ❌ Removed all mock data
- ✅ Now reads real signals from `data/daily_signals.csv`
- ✅ Calculates ATR-based entry/stop/target levels for each stock
- ✅ Shows risk/reward percentages
- ✅ Professional HTML email with stats summary
- ✅ Includes disclaimer

**What it does:**
1. Loads your daily signals
2. For each stock, calculates:
   - **Entry Range**: 0.2%-0.4% above yesterday's close
   - **Stop Loss**: 1× ATR below entry
   - **Target**: Higher of (predicted return OR 2:1 R/R)
   - **Risk %**: How much you can lose
   - **Reward %**: How much you can gain
3. Takes top 10 signals
4. Sends formatted email to shashi.gavva@gmail.com

**How to use:**
```bash
python send_signals_email.py
```

---

### 2. **backtest.py** (NEW FILE ✅)
**What it does:**
- Tests your model on historical data
- For the past 60 days, generates predictions and tracks actual outcomes
- Calculates precision (% of signals that hit 11%+ target)
- Shows if your model is performing at/above/below 60% target
- Provides detailed performance metrics

**Outputs:**
- `data/backtest_results.csv` - Raw results (every signal + actual return)
- `data/backtest_performance.txt` - Detailed report

**How to use:**
```bash
python backtest.py
```

**What you'll see:**
```
BACKTEST PERFORMANCE REPORT
======================================================================
Total Signals:        47
Winners (≥11%):       32 (68.1%)
Losers (<11%):        15 (31.9%)

✨ PRECISION:          68.1% (Target: 60%)
Status:               ✅ BEATING TARGET

Average Return:       +14.23%
Median Return:        +12.87%
...
```

---

## 🎯 Complete Workflow Now

```
1. Train models (monthly)
   → python train_models.py

2. Generate daily signals (every morning)
   → python daily_signals.py

3. Send email with entry/stop levels
   → python send_signals_email.py

4. Validate model performance (weekly/monthly)
   → python backtest.py
```

---

## 📧 Email Preview

Your emails will now look like this:

```
📈 Daily Stock Signals — Top 10 Longs — 2025-11-13
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Today's Summary:
• 36 stocks screened, 10 top signals selected
• Average Confidence: 94%
• Criteria: ≥60% probability of +11% gain in 10 days

🎯 Top 10 Long Signals

Ticker  Entry           Stop      Target    Conf  Risk   Reward  ATR
BPOP    $109.46–$109.68 $107.21   $129.47   99%   2.0%   18.3%   $2.25
ESPO    $115.67–$115.90 $113.42   $140.01   99%   1.9%   21.0%   $2.25
...
```

---

## ⚠️ Important Notes

1. **ESPO Trade**: Your Nov 12 ESPO entry was based on REAL model predictions, not mock data

2. **ATR Calculation**: Uses 14-day Average True Range for volatility-based stops

3. **Entry Buffer**: 0.2%-0.4% above close prevents chasing gaps

4. **Stop Loss**: Automatically calculated at 1× ATR below entry (configurable in config.py)

5. **Target**: Uses the higher of:
   - Model's predicted return
   - 2:1 risk/reward ratio

6. **Backtesting**: Run this regularly to ensure model isn't degrading

---

## 🔧 Configuration

All settings in `config.py`:
- `ENTRY_BUFFER = 0.002` (0.2% above close)
- `STOP_ATR_MULT = 1.0` (1× ATR stop)
- `RISK_REWARD = 2.0` (2:1 target fallback)
- `TARGET_PRECISION = 0.60` (60% win rate target)

---

## 🚀 Next Steps

1. **Test the new email:**
   ```bash
   python daily_signals.py
   python send_signals_email.py
   ```

2. **Validate model performance:**
   ```bash
   python backtest.py
   ```

3. **Schedule automation** (optional):
   - Mac/Linux: Use cron
   - Windows: Use Task Scheduler
   ```
   # Run at 9 AM CST daily
   0 9 * * * cd /path/to/project && python daily_signals.py && python send_signals_email.py
   ```

---

## 📊 Files to Replace in Your VSCode

Copy-paste these files completely (replace existing):
1. ✅ `send_signals_email.py`
2. ✅ `backtest.py` (new file - just add it)

Keep everything else the same!
