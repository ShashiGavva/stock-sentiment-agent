import os
import pandas as pd
import yfinance as yf
from datetime import datetime
from send_email import send_email
import config

# =====================================================
# LOAD DAILY SIGNALS
# =====================================================
SIGNALS_PATH = "data/daily_signals.csv"

if not os.path.exists(SIGNALS_PATH):
    print(f"❌ No signals file found at {SIGNALS_PATH}")
    print("Run daily_signals.py first to generate signals.")
    exit(1)

df_signals = pd.read_csv(SIGNALS_PATH)

if df_signals.empty:
    print("⚠️ No signals to send today.")
    exit(0)

print(f"📊 Loaded {len(df_signals)} signals from {SIGNALS_PATH}")

# =====================================================
# CALCULATE ENTRY & STOP LEVELS
# =====================================================
def calculate_atr(symbol, period=14):
    """Calculate Average True Range for a symbol."""
    try:
        df = yf.download(symbol, period="1mo", interval="1d", progress=False, auto_adjust=True)
        if df.empty:
            return None
        
        # Calculate True Range
        df['high_low'] = df['High'] - df['Low']
        df['high_close'] = abs(df['High'] - df['Close'].shift())
        df['low_close'] = abs(df['Low'] - df['Close'].shift())
        df['tr'] = df[['high_low', 'high_close', 'low_close']].max(axis=1)
        
        # ATR is average of True Range
        atr = df['tr'].rolling(window=period).mean().iloc[-1]
        return atr
    except Exception as e:
        print(f"⚠️ Could not calculate ATR for {symbol}: {e}")
        return None


def calculate_trade_levels(row):
    """Calculate entry, stop, and target levels based on config."""
    symbol = row['symbol']
    close = row['latest_close']
    predicted_return = row['predicted_return_q90'] / 100  # convert from percentage
    
    # Get ATR
    atr = calculate_atr(symbol)
    if atr is None:
        atr = close * config.MIN_ATR_PCT  # fallback to minimum ATR
    
    # Entry: slightly above last close
    entry_low = close * (1 + config.ENTRY_BUFFER)
    entry_high = close * (1 + config.ENTRY_BUFFER * 2)
    
    # Stop: ATR below entry
    stop = entry_low - (atr * config.STOP_ATR_MULT)
    
    # Target: use predicted return or risk/reward ratio, whichever is higher
    target_predicted = close * (1 + predicted_return)
    target_risk_reward = entry_low + ((entry_low - stop) * config.RISK_REWARD)
    target = max(target_predicted, target_risk_reward)
    
    # Risk percentage
    risk_pct = ((entry_low - stop) / entry_low) * 100
    
    # Reward percentage
    reward_pct = ((target - entry_low) / entry_low) * 100
    
    return {
        'entry_range': f"${entry_low:.2f}–${entry_high:.2f}",
        'stop': f"${stop:.2f}",
        'target': f"${target:.2f}",
        'risk_pct': f"{risk_pct:.1f}%",
        'reward_pct': f"{reward_pct:.1f}%",
        'atr': f"${atr:.2f}"
    }


# Calculate levels for all signals
print("📐 Calculating entry/stop/target levels...")
trade_levels = []
for idx, row in df_signals.iterrows():
    levels = calculate_trade_levels(row)
    trade_levels.append({
        'Ticker': row['symbol'],
        'Entry': levels['entry_range'],
        'Stop': levels['stop'],
        'Target': levels['target'],
        'Conf': int(row['prob_11pct_up'] * 100),
        'Risk': levels['risk_pct'],
        'Reward': levels['reward_pct'],
        'ATR': levels['atr']
    })

df_trades = pd.DataFrame(trade_levels)

# Take top 10 for email
df_top10 = df_trades.head(10)

print(f"✅ Prepared {len(df_top10)} signals for email")

# =====================================================
# BUILD HTML EMAIL
# =====================================================
def df_to_html_table(df: pd.DataFrame) -> str:
    """Convert dataframe to clean HTML table."""
    return df.to_html(
        index=False, 
        border=0, 
        justify="center",
        classes="tbl",
        escape=False
    )


today = datetime.now().strftime("%Y-%m-%d")
subject = f"📈 Daily Stock Signals — Top 10 Longs — {today}"

html = f"""
<html>
  <head>
    <style>
      body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
        color: #0b0b0b;
        line-height: 1.6;
        max-width: 900px;
        margin: 0 auto;
        padding: 20px;
      }}
      h2 {{
        margin-bottom: 4px;
        color: #1a1a1a;
      }}
      .date {{
        font-size: 12px;
        color: #666;
        margin-bottom: 16px;
      }}
      h3 {{
        margin: 20px 0 10px;
        color: #2c2c2c;
        border-bottom: 2px solid #e5e5e5;
        padding-bottom: 5px;
      }}
      table.tbl {{
        width: 100%;
        border-collapse: collapse;
        margin: 16px 0;
        font-size: 13px;
      }}
      table.tbl th {{
        background: #f8f9fa;
        padding: 10px;
        text-align: left;
        font-weight: 600;
        border-bottom: 2px solid #dee2e6;
      }}
      table.tbl td {{
        padding: 8px 10px;
        border-bottom: 1px solid #e9ecef;
      }}
      table.tbl tr:hover {{
        background: #f8f9fa;
      }}
      .footer {{
        margin-top: 30px;
        padding-top: 20px;
        border-top: 1px solid #dee2e6;
        font-size: 11px;
        color: #666;
        line-height: 1.5;
      }}
      .stats {{
        background: #f0f7ff;
        padding: 12px;
        border-radius: 4px;
        margin: 16px 0;
        font-size: 13px;
      }}
    </style>
  </head>
  <body>
    <h2>📈 Daily Stock Signals</h2>
    <div class="date">{today}</div>

    <div class="stats">
      <strong>Today's Summary:</strong> {len(df_signals)} stocks screened, {len(df_top10)} top signals selected<br>
      <strong>Average Confidence:</strong> {df_top10['Conf'].mean():.0f}%<br>
      <strong>Criteria:</strong> ≥60% probability of +11% gain in 10 days
    </div>

    <h3>🎯 Top 10 Long Signals</h3>
    <div style="overflow-x:auto">
      {df_to_html_table(df_top10)}
    </div>

    <div class="footer">
      <strong>How to Use:</strong><br>
      • <strong>Entry:</strong> Preferred buy range (0.2%-0.4% above yesterday's close)<br>
      • <strong>Stop:</strong> Exit if price falls to this level (1× ATR below entry)<br>
      • <strong>Target:</strong> Take profit target (based on predicted return or 2:1 R/R)<br>
      • <strong>Conf:</strong> Model confidence (0-100%)<br>
      • <strong>Risk/Reward:</strong> Expected loss vs gain percentages<br>
      • <strong>ATR:</strong> Average True Range (14-day volatility measure)<br>
      <br>
      <strong>⚠️ DISCLAIMER:</strong> This is an experimental ML system for educational purposes only. 
      Not financial advice. Past performance does not guarantee future results. 
      Always do your own research and risk only what you can afford to lose.
    </div>
  </body>
</html>
"""

# =====================================================
# SEND EMAIL
# =====================================================
try:
    send_email("shashi.gavva@gmail.com", subject, html)
    print(f"\n✅ Email sent successfully to shashi.gavva@gmail.com")
    print(f"📧 Subject: {subject}")
except Exception as e:
    print(f"❌ Failed to send email: {e}")
