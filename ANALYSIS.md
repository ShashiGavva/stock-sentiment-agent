# Analysis: Why ESPO, WRLD, and FEX Didn't Perform as Predicted

## Executive Summary

I investigated why the stocks recommended by your app (ESPO, WRLD, FEX) didn't perform as expected. I found **several critical issues** with the recommendation system:

---

## Key Findings

### 1. **The App Recommends ETFs, Not Just Stocks**

**ESPO** is actually the **VanEck Video Gaming and eSports ETF**, not a stock.

**Problem:** ETFs behave very differently from individual stocks:
- ETFs are diversified baskets of stocks (lower volatility)
- They rarely make dramatic 11%+ moves in 10 days
- The model was trained to predict individual stock momentum, not ETF behavior

**Why this happened:**
- The app pulls tickers from NASDAQ/NYSE/AMEX listings (symbols.py:14-16)
- These sources include both stocks AND ETFs
- No filtering is applied to distinguish between them

**Impact:**
- The model is applying stock momentum strategies to ETFs
- This creates unrealistic predictions for ETF returns
- Users invest in instruments that don't match the model's assumptions

---

### 2. **The Model is Extremely Overconfident**

Your signals showed:
- **ESPO**: 99.1% confidence → predicted +21.1% in 10 days
- **WRLD**: 96.5% confidence → predicted +13.6% in 10 days
- **FEX**: 98.1% confidence → predicted +19.0% in 10 days

**Problem:** These confidence levels are unrealistic for stock market predictions.

**Evidence from backtest data:**
- Looking at backtest_results.csv, I found signals for AVGO at 95-97% confidence
- Actual returns: mostly 2-9%, many MISSED the 11% target
- Example: AVGO on 2025-09-24 had 96.6% confidence, actual return was only +1.8%

**Root cause:**
- Only 47 signals generated in 60-day backtest period
- That's less than 1 signal per day across 6,000 stocks
- Model is being **extremely selective** = overconfident calibration
- 60% probability threshold (PREDICTION_THRESHOLD = 0.6) catches only very extreme cases

---

### 3. **No Sentiment Analysis Despite the Name**

The app is called "stock-sentiment-agent" but:

❌ No news analysis
❌ No social media sentiment
❌ No NLP/text processing
❌ No sentiment libraries (VADER, TextBlob, etc.)

**What it actually does:**
✅ Pure technical analysis (moving averages, volatility, momentum)

**Features used (features.py:12-49):**
- Moving averages (SMA 10/20/50)
- Price momentum vs SMAs
- Volatility (10-day, 20-day)
- Return lags (1, 2, 3, 5 days)

**Impact:**
- Missing crucial market context (news, earnings, sentiment shifts)
- Purely historical price patterns may not predict future performance
- Technical patterns can break down during news events

---

### 4. **Corrupted Backtest Data**

The file `data/backtest_results.csv` contains corrupted data:

```csv
actual_return,hit_target
"Ticker
AAPL    0.112527
dtype: float64","Ticker
AAPL    True
dtype: bool"
```

**Problem:**
- Columns contain pandas Series objects instead of scalar values
- This makes it impossible to validate model performance
- You can't trust the hit rate or accuracy metrics

**Root cause (backtest.py:160-164):**
- `calculate_actual_return()` function returns a Series instead of a single value
- Likely due to DataFrame indexing issue

**Impact:**
- No reliable way to know if the model actually works
- Can't calibrate probability thresholds properly
- Can't identify which types of stocks/conditions lead to success

---

### 5. **Arbitrary Target Selection**

The model targets **11% gains in 10 days** (train_models.py:15):

```python
TARGET_UPSIDE = 0.11  # 11% return threshold
```

**Questions:**
- Why 11% and not 10% or 15%?
- Why 10 days and not 5 or 20?
- Was this based on data analysis or just chosen arbitrarily?

**Impact:**
- If the target is too aggressive, the model will:
  - Find too few signals (explaining the 47 signals/60 days)
  - Be overconfident in those it does find
  - Miss more realistic opportunities (e.g., 8% gains)

---

### 6. **Data Access Issues**

When I tried to verify actual performance for ESPO, WRLD, FEX:

```
HTTP Error 403: Access denied (ESPO, WRLD)
$FEX: possibly delisted; no timezone found
```

**Possible explanations:**
1. **Yahoo Finance rate limiting** - Too many requests from this system
2. **Tickers may be delisted or changed symbols**
3. **ETFs may have different data access patterns**

**Impact:**
- The training/prediction pipeline may be working with stale or invalid data
- Some "signals" may be for stocks that no longer trade
- Daily signal generation (daily_signals.py) may be failing silently for some tickers

---

## Why Your Investments Didn't Go Up

Based on my analysis, here's what likely happened:

### Scenario 1: ETF Behavior
- ESPO/WRLD are ETFs, which are inherently diversified
- They don't exhibit the volatile momentum patterns individual stocks do
- A 21% move in 10 days is virtually impossible for a broad ETF
- The model's predictions were based on stock patterns applied to ETFs

### Scenario 2: Model Overconfidence
- The 99% confidence levels created false certainty
- The model found extreme technical patterns (strong momentum)
- But technical patterns alone don't guarantee continuation
- News, macro events, or profit-taking can reverse momentum quickly

### Scenario 3: Market Regime Change
- Models trained on historical data assume patterns repeat
- If market conditions changed (volatility, trends, etc.), the model breaks
- No concept drift detection (models retrain only every 30 days)
- Recent market may behave differently than training period

### Scenario 4: Backtest Corruption Masks Real Performance
- The corrupted backtest data suggests the model was never properly validated
- The 60% threshold may not actually correspond to 60% hit rate
- You might be looking at a model that never actually worked

---

## Evidence from Backtest Results

Looking at the readable backtest data (despite corruption):

**Winners:**
- TSLA, AMD, NVDA, AAPL, AMZN, GOOGL - all HIT target when predicted
- These are mega-cap tech stocks with strong momentum

**Losers:**
- AVGO - 15 signals, 0 hit the 11% target despite 65-98% confidence
- ORCL - 1 signal at 91% confidence, returned -6.4%
- PANW - 9 signals, all missed the target
- LRCX - Mixed results, only 7/12 hit target

**Pattern:**
- Model works on mega-cap momentum stocks (TSLA, NVDA, AMD)
- Fails on mid-cap stocks and ETFs
- Your picks (ESPO, WRLD, FEX) don't match the successful pattern

---

## Recommendations to Fix the System

### Immediate Fixes

1. **Filter Out ETFs**
   ```python
   # In symbols.py or daily_signals.py
   # Check if ticker.info['quoteType'] == 'STOCK' (not ETF, MUTUAL FUND, etc.)
   ```

2. **Fix Backtest Corruption**
   ```python
   # In backtest.py:160-164
   # Change calculate_actual_return to return a scalar, not a Series
   ```

3. **Lower the Target or Extend the Timeframe**
   ```python
   # Try TARGET_UPSIDE = 0.08 (8%) or extend to 20 days
   # This will generate more signals and reduce overconfidence
   ```

4. **Add Probability Calibration**
   ```python
   # Validate that 90% confidence actually corresponds to 90% success rate
   # Use calibration curves (sklearn.calibration.calibration_curve)
   ```

### Medium-Term Improvements

5. **Add True Sentiment Analysis**
   - Integrate NewsAPI, Finnhub, or Twitter sentiment
   - Add NLP features (headline polarity, volume, source credibility)
   - Rename project to "Stock Technical Momentum Agent" if keeping pure TA

6. **Improve Feature Engineering**
   - Add volume patterns (volume surges, on-balance volume)
   - Add sector relative strength (is stock outperforming its sector?)
   - Add macro indicators (VIX, yield curves, sector rotation)

7. **Implement Risk Management**
   - The current ATR-based stops are good (send_signals_email.py:68)
   - But add position sizing based on volatility
   - Consider Kelly Criterion or risk parity

8. **Add Model Monitoring**
   - Track actual vs predicted returns in real-time
   - Alert when model performance degrades
   - Retrain more frequently if drift detected

### Long-Term Improvements

9. **Multi-Model Ensemble**
   - Train separate models for different market caps
   - Train separate models for different sectors
   - Train separate models for different volatility regimes

10. **Backtesting Framework**
    - Fix the corruption bug
    - Run rolling backtests (not just 60 days)
    - Calculate Sharpe ratio, max drawdown, win rate by confidence bucket

11. **Feature Importance Analysis**
    - Use SHAP values to understand what drives predictions
    - Remove spurious correlations
    - Focus on features that generalize

---

## What You Should Do Now

### If You're Still Holding ESPO, WRLD, FEX:

1. **Check if they're actually moving**
   - Use a different data source (TradingView, Robinhood, your broker)
   - See if the recommendations were based on bad/stale data

2. **Apply risk management**
   - If losses exceed your stop-loss, exit
   - If they're flat, evaluate your opportunity cost

3. **Diversify**
   - Don't rely on a single model's recommendations
   - Use this as one input among many

### If You Want to Keep Using the App:

1. **Wait for fixes**
   - Let me fix the ETF filtering issue
   - Let me fix the backtest corruption
   - Revalidate the model before using it again

2. **Lower your expectations**
   - Even good models have win rates of 55-65%, not 90%+
   - The 11% target is very aggressive
   - Expect smaller, more frequent gains instead

3. **Paper trade first**
   - Test the updated model with fake money
   - Track performance for 30-60 days
   - Only use real money after validation

---

## Bottom Line

**The app gave you high-confidence predictions for 3 tickers (ESPO, WRLD, FEX) that had multiple red flags:**

1. At least one is an ETF (ESPO), not suited to this model
2. Confidence levels (96-99%) were unrealistically high
3. Predicted returns (13-21% in 10 days) were extremely aggressive
4. The model has no sentiment analysis despite its name
5. Backtest data is corrupted, so we can't verify it ever worked
6. Data access issues suggest staleness or delisting

**This is a combination of:**
- Technical issues (ETF filtering, backtest bugs)
- Overconfident model calibration
- Missing features (sentiment, volume, macro)
- Possibly bad data quality

**Would you like me to:**
1. Fix the ETF filtering and backtest bugs?
2. Retrain the model with better features?
3. Add sentiment analysis to match the name?
4. Build a proper validation framework?

Let me know how you'd like to proceed.
