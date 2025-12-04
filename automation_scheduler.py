"""
Daily Automation Scheduler for Day Trading
- 8:30 AM CST: Run daily_signals.py and populate watchlist with top 10 signals
- 9:00 AM CST: Start day trading automation with 5-minute intervals
- Runs until market close (4:00 PM EST / 3:00 PM CST)
- Sends end-of-day digest
"""
import os
import sys
import time
import json
import pickle
import smtplib
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import pytz

# Import project modules
import config
from features import build_features
from symbols import get_sp500_tickers
from utils import is_valid_stock
from intraday_features import build_intraday_features, generate_day_trading_signals, get_market_status

# CST timezone
CST = pytz.timezone('America/Chicago')
EST = pytz.timezone('America/New_York')

# Paths
SIGNALS_CSV = os.path.join(config.DATA_DIR, 'daily_signals.csv')
WATCHLIST_FILE = os.path.join(config.DATA_DIR, 'automation_watchlist.json')
POSITIONS_FILE = os.path.join(config.DATA_DIR, 'automation_positions.json')
TRADES_FILE = os.path.join(config.DATA_DIR, 'automation_trades.json')
DIGEST_FILE = os.path.join(config.DATA_DIR, 'daily_digest.txt')

# Trading parameters
INITIAL_INVESTMENT = 1000  # $1000 for first buy signal
SUBSEQUENT_INVESTMENT = 250  # $250 for additional buys
MAX_POSITION_SIZE = 3000  # Maximum per position


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def fetch_data(symbol, period="3mo", interval="1d"):
    """Fetch OHLCV data for a given symbol."""
    try:
        df = yf.download(symbol, period=period, interval=interval, progress=False, auto_adjust=True)
        if df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [c[0] for c in df.columns]
        df = df.reset_index().rename(
            columns={
                "Date": "date",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Adj Close": "adj_close",
                "Volume": "volume",
            }
        )
        return df
    except Exception as e:
        print(f"⚠️ {symbol}: {e}")
        return None


def get_current_price(symbol):
    """Get current price for a symbol."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period='1d', interval='1m')
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None


def load_json_file(filepath, default=None):
    """Load JSON file with error handling."""
    if default is None:
        default = []
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading {filepath}: {e}")
    return default


def save_json_file(filepath, data):
    """Save data to JSON file."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Error saving {filepath}: {e}")
        return False


# ============================================================================
# SIGNAL GENERATION (8:30 AM CST)
# ============================================================================

def generate_daily_signals():
    """Run daily_signals.py and populate watchlist with top 10 signals."""
    print("\n" + "=" * 70)
    print(f"🔍 DAILY SIGNAL GENERATION - {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 70)

    try:
        # Load models
        print("📦 Loading models...")
        with open(config.CLF_PATH, "rb") as f:
            clf_pack = pickle.load(f)
        with open(config.Q90_PATH, "rb") as f:
            reg_pack = pickle.load(f)
        clf = clf_pack["model"]
        reg = reg_pack["model"]

        # Get tickers
        print("🔍 Fetching tickers...")
        if config.USE_SP500_ONLY:
            tickers = get_sp500_tickers()
        else:
            from symbols import get_all_us_tickers
            tickers = get_all_us_tickers()
        print(f"✅ Loaded {len(tickers)} tickers")

        # Generate signals
        all_signals = []
        MIN_VOLUME = 100000
        PREDICTION_THRESHOLD = config.CONFIDENCE_TIERS['medium']

        for i, sym in enumerate(tickers):
            if i % 50 == 0:
                print(f"📊 Processing {i}/{len(tickers)}...")

            df = fetch_data(sym)
            if df is None:
                continue

            # Build features (no sentiment)
            feats = build_features(df, symbol=sym, include_sentiment=False)
            if feats is None or feats.empty:
                continue

            # Validate stock
            validation = is_valid_stock(sym, min_volume=MIN_VOLUME)
            if not validation['is_valid']:
                continue

            # Prepare features
            drop_cols = ["future_return_10d", "target_hit", "date", "symbol"]
            X = (
                feats.drop(columns=drop_cols, errors="ignore")
                .select_dtypes(include=[np.number])
                .iloc[-1:]
            )

            try:
                proba = clf.predict_proba(X)[0, 1]
                pred_q90 = reg.predict(X)[0]
            except Exception as e:
                continue

            if proba >= PREDICTION_THRESHOLD:
                all_signals.append({
                    "symbol": sym,
                    "prob_11pct_up": round(proba, 3),
                    "predicted_return_q90": round(pred_q90 * 100, 2),
                    "latest_close": float(feats["close"].iloc[-1]),
                    "date": datetime.today().strftime("%Y-%m-%d"),
                })

        if all_signals:
            # Sort by probability and save
            df_out = pd.DataFrame(all_signals).sort_values(by="prob_11pct_up", ascending=False)
            df_out.to_csv(SIGNALS_CSV, index=False)

            # Get top 10 signals for watchlist
            top_10 = df_out.head(10)['symbol'].tolist()
            save_json_file(WATCHLIST_FILE, {
                'symbols': top_10,
                'generated_at': datetime.now(CST).isoformat(),
                'total_signals': len(df_out)
            })

            print(f"\n✅ Generated {len(df_out)} signals")
            print(f"📊 Top 10 watchlist: {', '.join(top_10)}")
            print(f"💾 Saved to {SIGNALS_CSV}")

            return top_10
        else:
            print("⚠️ No signals generated today.")
            return []

    except Exception as e:
        print(f"❌ Error generating signals: {e}")
        import traceback
        traceback.print_exc()
        return []


# ============================================================================
# DAY TRADING AUTOMATION (9:00 AM CST - 3:00 PM CST)
# ============================================================================

def execute_trade(symbol, signal_type, price, amount_usd):
    """Execute a trade (simulated - logs the trade)."""
    shares = amount_usd / price if price > 0 else 0

    trade = {
        'symbol': symbol,
        'signal': signal_type,
        'price': round(price, 2),
        'amount_usd': amount_usd,
        'shares': round(shares, 4),
        'timestamp': datetime.now(CST).isoformat()
    }

    print(f"  💵 {signal_type} {shares:.2f} shares @ ${price:.2f} = ${amount_usd:.2f}")
    return trade


def process_trading_cycle():
    """Process one trading cycle - check signals and manage positions."""
    print("\n" + "-" * 70)
    print(f"🔄 Trading Cycle - {datetime.now(CST).strftime('%H:%M:%S %Z')}")
    print("-" * 70)

    # Load watchlist and positions
    watchlist_data = load_json_file(WATCHLIST_FILE, {'symbols': []})
    watchlist = watchlist_data.get('symbols', [])
    positions = load_json_file(POSITIONS_FILE, {})
    trades_today = load_json_file(TRADES_FILE, [])

    if not watchlist:
        print("⚠️ No watchlist loaded. Waiting for 8:30 AM signal generation.")
        return

    print(f"📊 Monitoring: {', '.join(watchlist)}")

    # Process each symbol in watchlist
    for symbol in watchlist:
        try:
            # Get intraday data and signals
            df = build_intraday_features(symbol, interval='5m', days_back=1)
            if df is None or df.empty:
                continue

            signals = generate_day_trading_signals(df)
            if not signals:
                continue

            current_price = get_current_price(symbol)
            if current_price is None:
                continue

            # Check position status
            position = positions.get(symbol, {})
            has_position = bool(position)

            print(f"\n  📈 {symbol}: ${current_price:.2f}")

            # Process signals
            for sig in signals:
                signal_type = sig['type']

                if signal_type == 'BUY' and not has_position:
                    # First buy: $1000
                    trade = execute_trade(symbol, 'BUY', current_price, INITIAL_INVESTMENT)
                    positions[symbol] = {
                        'entry_price': current_price,
                        'total_invested': INITIAL_INVESTMENT,
                        'shares': trade['shares'],
                        'trades': [trade]
                    }
                    trades_today.append(trade)
                    print(f"  ✅ Opened position in {symbol}")

                elif signal_type == 'BUY' and has_position:
                    # Subsequent buy: $250 (if under max position size)
                    current_invested = position['total_invested']
                    if current_invested + SUBSEQUENT_INVESTMENT <= MAX_POSITION_SIZE:
                        trade = execute_trade(symbol, 'BUY', current_price, SUBSEQUENT_INVESTMENT)
                        position['total_invested'] += SUBSEQUENT_INVESTMENT
                        position['shares'] += trade['shares']
                        position['trades'].append(trade)
                        trades_today.append(trade)
                        print(f"  ✅ Added to position in {symbol} (Total: ${position['total_invested']:.2f})")
                    else:
                        print(f"  ⚠️ Max position size reached for {symbol}")

                elif signal_type == 'SELL' and has_position:
                    # Sell entire position
                    shares = position['shares']
                    total_invested = position['total_invested']
                    proceeds = shares * current_price
                    profit_loss = proceeds - total_invested
                    profit_loss_pct = (profit_loss / total_invested) * 100 if total_invested > 0 else 0

                    trade = execute_trade(symbol, 'SELL', current_price, proceeds)
                    trade['profit_loss'] = round(profit_loss, 2)
                    trade['profit_loss_pct'] = round(profit_loss_pct, 2)
                    trade['shares_sold'] = shares

                    trades_today.append(trade)

                    print(f"  🔴 Closed position in {symbol}")
                    print(f"     P&L: ${profit_loss:+.2f} ({profit_loss_pct:+.1f}%)")

                    # Remove position
                    del positions[symbol]

        except Exception as e:
            print(f"  ⚠️ Error processing {symbol}: {e}")
            continue

    # Save updated positions and trades
    save_json_file(POSITIONS_FILE, positions)
    save_json_file(TRADES_FILE, trades_today)

    print(f"\n💼 Active positions: {len(positions)}")
    print("-" * 70)


# ============================================================================
# END OF DAY DIGEST
# ============================================================================

def generate_digest():
    """Generate and send end-of-day digest."""
    print("\n" + "=" * 70)
    print(f"📧 GENERATING END-OF-DAY DIGEST - {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 70)

    # Load data
    trades_today = load_json_file(TRADES_FILE, [])
    positions = load_json_file(POSITIONS_FILE, {})
    watchlist_data = load_json_file(WATCHLIST_FILE, {'symbols': []})

    # Calculate metrics
    total_trades = len(trades_today)
    buys = [t for t in trades_today if t['signal'] == 'BUY']
    sells = [t for t in trades_today if t['signal'] == 'SELL']

    total_pnl = sum(t.get('profit_loss', 0) for t in sells)
    winning_trades = sum(1 for t in sells if t.get('profit_loss', 0) > 0)
    losing_trades = sum(1 for t in sells if t.get('profit_loss', 0) < 0)

    win_rate = (winning_trades / len(sells) * 100) if sells else 0

    # Build digest
    digest = f"""
{'=' * 70}
DAY TRADING DIGEST - {datetime.now(CST).strftime('%Y-%m-%d')}
{'=' * 70}

📊 WATCHLIST
{', '.join(watchlist_data.get('symbols', []))}
Total signals generated: {watchlist_data.get('total_signals', 0)}

📈 TRADING ACTIVITY
Total trades executed: {total_trades}
  - Buy orders: {len(buys)}
  - Sell orders: {len(sells)}

💰 PERFORMANCE
Total P&L: ${total_pnl:+.2f}
Winning trades: {winning_trades}
Losing trades: {losing_trades}
Win rate: {win_rate:.1f}%

💼 OPEN POSITIONS ({len(positions)})
"""

    for symbol, pos in positions.items():
        current_price = get_current_price(symbol)
        if current_price:
            unrealized_pnl = (current_price * pos['shares']) - pos['total_invested']
            unrealized_pct = (unrealized_pnl / pos['total_invested']) * 100 if pos['total_invested'] > 0 else 0
            digest += f"\n  {symbol}: {pos['shares']:.2f} shares @ avg ${pos['entry_price']:.2f}"
            digest += f"\n    Current: ${current_price:.2f} | Unrealized P&L: ${unrealized_pnl:+.2f} ({unrealized_pct:+.1f}%)"

    if not positions:
        digest += "\n  No open positions"

    digest += f"\n\n📝 DETAILED TRADES\n"
    for i, trade in enumerate(trades_today, 1):
        digest += f"\n{i}. {trade['timestamp'][:19]} - {trade['signal']} {trade['symbol']}"
        digest += f"\n   {trade['shares']:.2f} shares @ ${trade['price']:.2f} = ${trade['amount_usd']:.2f}"
        if 'profit_loss' in trade:
            digest += f"\n   P&L: ${trade['profit_loss']:+.2f} ({trade['profit_loss_pct']:+.1f}%)"

    if not trades_today:
        digest += "\n  No trades executed today"

    digest += f"\n\n{'=' * 70}\n"

    # Save digest
    with open(DIGEST_FILE, 'w') as f:
        f.write(digest)

    print(digest)
    print(f"💾 Digest saved to {DIGEST_FILE}")

    # TODO: Send email digest
    # send_email_digest(digest)

    return digest


def send_email_digest(digest_text):
    """Send digest via email (placeholder for email configuration)."""
    # TODO: Configure email settings
    # This requires SMTP server details, which should be added to config.py
    pass


# ============================================================================
# SCHEDULER SETUP
# ============================================================================

def run_8_30am_task():
    """8:30 AM CST - Generate signals and populate watchlist."""
    generate_daily_signals()


def run_9am_task():
    """9:00 AM CST - Initial trading cycle start."""
    print("\n🚀 Starting day trading automation...")
    process_trading_cycle()


def run_3pm_task():
    """3:00 PM CST (Market close) - Generate digest."""
    generate_digest()

    # Clear positions file for next day (optional - keep if you want overnight holds)
    # save_json_file(POSITIONS_FILE, {})
    # save_json_file(TRADES_FILE, [])


def is_weekday():
    """Check if today is a weekday."""
    return datetime.now(CST).weekday() < 5  # Monday=0, Friday=4


def should_run_today():
    """Check if we should run today (weekday only)."""
    if not is_weekday():
        print(f"📅 Today is {datetime.now(CST).strftime('%A')} - Skipping (weekend)")
        return False
    return True


# ============================================================================
# MAIN SCHEDULER
# ============================================================================

def main():
    """Main scheduler loop."""
    print("\n" + "=" * 70)
    print("🤖 DAY TRADING AUTOMATION SCHEDULER")
    print("=" * 70)
    print(f"Timezone: America/Chicago (CST)")
    print(f"Schedule:")
    print(f"  • 8:30 AM CST - Generate daily signals & populate watchlist")
    print(f"  • 9:00 AM CST - Start day trading automation")
    print(f"  • Every 5 min (9:00 AM - 3:00 PM CST) - Process trading signals")
    print(f"  • 3:00 PM CST - Generate end-of-day digest")
    print("=" * 70)

    # Schedule tasks
    schedule.every().day.at("08:30").do(lambda: should_run_today() and run_8_30am_task())
    schedule.every().day.at("09:00").do(lambda: should_run_today() and run_9am_task())
    schedule.every().day.at("15:00").do(lambda: should_run_today() and run_3pm_task())

    # Schedule 5-minute trading cycles between 9 AM and 3 PM
    for hour in range(9, 15):  # 9 AM to 3 PM
        for minute in range(0, 60, 5):  # Every 5 minutes
            time_str = f"{hour:02d}:{minute:02d}"
            schedule.every().day.at(time_str).do(lambda: should_run_today() and process_trading_cycle())

    print(f"✅ Scheduler started at {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("🔄 Running continuously... (Press Ctrl+C to stop)\n")

    # Run scheduler
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped by user")


if __name__ == "__main__":
    # For testing: uncomment to run specific tasks immediately
    # generate_daily_signals()
    # process_trading_cycle()
    # generate_digest()

    main()
