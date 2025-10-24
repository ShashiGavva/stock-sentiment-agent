# send_signals_email.py
import pandas as pd
from datetime import datetime
from send_email import send_email  # reuses your working sender

# --- 1) Mock signals (we'll replace with real data soon) ---
longs = [
    {"Ticker": "AMZN", "Entry": "180.5–181.2", "Stop": "177.9", "Conf": 83},
    {"Ticker": "NVDA", "Entry": "112.0–113.1", "Stop": "109.8", "Conf": 81},
    {"Ticker": "MSFT", "Entry": "412.2–413.0", "Stop": "408.7", "Conf": 78},
    {"Ticker": "META", "Entry": "498.0–500.0", "Stop": "492.5", "Conf": 76},
    {"Ticker": "NFLX", "Entry": "1187–1192", "Stop": "1169", "Conf": 74},
]

shorts = [
    {"Ticker": "ARKK", "Entry": "45.6–46.1", "Stop": "47.2", "Conf": 72},
    {"Ticker": "COIN", "Entry": "222–225", "Stop": "229", "Conf": 70},
    {"Ticker": "TSLA", "Entry": "221–223", "Stop": "226", "Conf": 69},
    {"Ticker": "PLTR", "Entry": "32.8–33.1", "Stop": "33.7", "Conf": 66},
    {"Ticker": "HOOD", "Entry": "19.3–19.5", "Stop": "19.9", "Conf": 64},
]

df_longs = pd.DataFrame(longs)
df_shorts = pd.DataFrame(shorts)

# --- 2) Simple HTML email ---
def df_to_html_table(df: pd.DataFrame) -> str:
    # minimal inline styling so it looks clean in Gmail
    return df.to_html(index=False, border=0, justify="center", classes="tbl")

today = datetime.now().strftime("%Y-%m-%d")
subject = f"Daily Signals — Top 10 Long / Top 10 Short — {today}"

html = f"""
<html>
  <body style="font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#0b0b0b;">
    <h2 style="margin-bottom:4px">Daily Signals</h2>
    <div style="font-size:12px;color:#666;margin-bottom:16px">{today}</div>

    <h3 style="margin:16px 0 6px">Top Longs</h3>
    <div style="overflow-x:auto">{df_to_html_table(df_longs)}</div>

    <h3 style="margin:20px 0 6px">Top Shorts</h3>
    <div style="overflow-x:auto">{df_to_html_table(df_shorts)}</div>

    <hr style="margin:20px 0">
    <div style="font-size:12px;color:#666;line-height:1.4">
      Entry = preferred range; Stop = soft stop; Conf = internal confidence (0–100).<br>
      This message is for educational purposes only and is <b>not financial advice</b>.
    </div>
  </body>
</html>
"""

# --- 3) Send to yourself (same inbox you used before) ---
# We don't need to pass a text_body—HTML renders nicely.
send_email("shashi.gavva@gmail.com", subject, html)
print("Sent signals email (mock).")

