"""
Automation Control Panel UI
Web interface to control and monitor day trading automation
"""
import os
import json
import pickle
import threading
import time
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np
import yfinance as yf
import pytz

# Import project modules
import config
from features import build_features
from symbols import get_sp500_tickers
from utils import is_valid_stock
from intraday_features import build_intraday_features, generate_day_trading_signals, get_market_status

app = Flask(__name__)

# Timezone
CST = pytz.timezone('America/Chicago')

# File paths
SIGNALS_CSV = os.path.join(config.DATA_DIR, 'daily_signals.csv')
WATCHLIST_FILE = os.path.join(config.DATA_DIR, 'automation_watchlist.json')
POSITIONS_FILE = os.path.join(config.DATA_DIR, 'automation_positions.json')
TRADES_FILE = os.path.join(config.DATA_DIR, 'automation_trades.json')
DIGEST_FILE = os.path.join(config.DATA_DIR, 'daily_digest.txt')

# Trading parameters
INITIAL_INVESTMENT = 1000
SUBSEQUENT_INVESTMENT = 250
MAX_POSITION_SIZE = 3000

# Global state
automation_state = {
    'signal_generation': {
        'status': 'idle',  # idle, running, complete, error
        'progress': 0,
        'total': 0,
        'current_ticker': '',
        'error': None,
        'last_run': None
    },
    'day_trading': {
        'status': 'idle',  # idle, running, stopped, error
        'is_active': False,
        'last_cycle': None,
        'error': None,
        'cycles_completed': 0
    },
    'ml_training': {
        'status': 'idle',  # idle, running, complete, error
        'progress': 0,
        'error': None,
        'last_run': None
    }
}

# Thread control
trading_thread_control = {'running': False}
state_lock = threading.Lock()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def load_json_file(filepath, default=None):
    """Load JSON file with error handling."""
    if default is None:
        default = {}
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
        return None


# ============================================================================
# SIGNAL GENERATION
# ============================================================================

def generate_signals_task():
    """Background task to generate daily signals."""
    global automation_state

    with state_lock:
        automation_state['signal_generation']['status'] = 'running'
        automation_state['signal_generation']['progress'] = 0
        automation_state['signal_generation']['error'] = None

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
        tickers = get_sp500_tickers()

        with state_lock:
            automation_state['signal_generation']['total'] = len(tickers)

        all_signals = []
        MIN_VOLUME = 100000
        PREDICTION_THRESHOLD = config.CONFIDENCE_TIERS['medium']

        for i, sym in enumerate(tickers):
            with state_lock:
                automation_state['signal_generation']['progress'] = i + 1
                automation_state['signal_generation']['current_ticker'] = sym

            df = fetch_data(sym)
            if df is None:
                continue

            feats = build_features(df, symbol=sym, include_sentiment=False)
            if feats is None or feats.empty:
                continue

            validation = is_valid_stock(sym, min_volume=MIN_VOLUME)
            if not validation['is_valid']:
                continue

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
                    "date": datetime.now(CST).strftime("%Y-%m-%d"),
                })

        if all_signals:
            df_out = pd.DataFrame(all_signals).sort_values(by="prob_11pct_up", ascending=False)
            df_out.to_csv(SIGNALS_CSV, index=False)

            # Get top 10 for watchlist
            top_10 = df_out.head(10)['symbol'].tolist()
            save_json_file(WATCHLIST_FILE, {
                'symbols': top_10,
                'generated_at': datetime.now(CST).isoformat(),
                'total_signals': len(df_out)
            })

            with state_lock:
                automation_state['signal_generation']['status'] = 'complete'
                automation_state['signal_generation']['last_run'] = datetime.now(CST).isoformat()
                automation_state['signal_generation']['current_ticker'] = ''

            print(f"✅ Generated {len(df_out)} signals, top 10: {', '.join(top_10)}")
        else:
            with state_lock:
                automation_state['signal_generation']['status'] = 'complete'
                automation_state['signal_generation']['error'] = 'No signals generated'

    except Exception as e:
        with state_lock:
            automation_state['signal_generation']['status'] = 'error'
            automation_state['signal_generation']['error'] = str(e)
        print(f"❌ Error generating signals: {e}")


# ============================================================================
# DAY TRADING
# ============================================================================

def execute_trade(symbol, signal_type, price, amount_usd):
    """Execute a trade (simulated)."""
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


def trading_cycle():
    """Execute one trading cycle."""
    print(f"🔄 Trading Cycle - {datetime.now(CST).strftime('%H:%M:%S %Z')}")

    watchlist_data = load_json_file(WATCHLIST_FILE, {'symbols': []})
    watchlist = watchlist_data.get('symbols', [])
    positions = load_json_file(POSITIONS_FILE, {})
    trades_today = load_json_file(TRADES_FILE, [])

    if not watchlist:
        print("⚠️ No watchlist loaded")
        return

    for symbol in watchlist:
        try:
            df = build_intraday_features(symbol, interval='5m', days_back=1)
            if df is None or df.empty:
                continue

            signals = generate_day_trading_signals(df)
            if not signals:
                continue

            current_price = get_current_price(symbol)
            if current_price is None:
                continue

            position = positions.get(symbol, {})
            has_position = bool(position)

            for sig in signals:
                signal_type = sig['type']

                if signal_type == 'BUY' and not has_position:
                    trade = execute_trade(symbol, 'BUY', current_price, INITIAL_INVESTMENT)
                    positions[symbol] = {
                        'entry_price': current_price,
                        'total_invested': INITIAL_INVESTMENT,
                        'shares': trade['shares'],
                        'trades': [trade],
                        'entry_time': trade['timestamp']
                    }
                    trades_today.append(trade)

                elif signal_type == 'BUY' and has_position:
                    current_invested = position['total_invested']
                    if current_invested + SUBSEQUENT_INVESTMENT <= MAX_POSITION_SIZE:
                        trade = execute_trade(symbol, 'BUY', current_price, SUBSEQUENT_INVESTMENT)
                        position['total_invested'] += SUBSEQUENT_INVESTMENT
                        position['shares'] += trade['shares']
                        position['trades'].append(trade)
                        trades_today.append(trade)

                elif signal_type == 'SELL' and has_position:
                    shares = position['shares']
                    total_invested = position['total_invested']
                    proceeds = shares * current_price
                    profit_loss = proceeds - total_invested
                    profit_loss_pct = (profit_loss / total_invested) * 100 if total_invested > 0 else 0

                    trade = execute_trade(symbol, 'SELL', current_price, proceeds)
                    trade['profit_loss'] = round(profit_loss, 2)
                    trade['profit_loss_pct'] = round(profit_loss_pct, 2)
                    trade['shares_sold'] = shares
                    trade['entry_price'] = position['entry_price']
                    trade['entry_time'] = position['entry_time']

                    trades_today.append(trade)
                    del positions[symbol]

        except Exception as e:
            print(f"  ⚠️ Error processing {symbol}: {e}")
            continue

    save_json_file(POSITIONS_FILE, positions)
    save_json_file(TRADES_FILE, trades_today)

    with state_lock:
        automation_state['day_trading']['last_cycle'] = datetime.now(CST).isoformat()
        automation_state['day_trading']['cycles_completed'] += 1


def day_trading_loop():
    """Main day trading loop."""
    global trading_thread_control

    with state_lock:
        automation_state['day_trading']['status'] = 'running'
        automation_state['day_trading']['is_active'] = True
        automation_state['day_trading']['cycles_completed'] = 0

    try:
        while trading_thread_control['running']:
            trading_cycle()
            time.sleep(300)  # 5 minutes

    except Exception as e:
        with state_lock:
            automation_state['day_trading']['status'] = 'error'
            automation_state['day_trading']['error'] = str(e)

    finally:
        with state_lock:
            automation_state['day_trading']['status'] = 'stopped'
            automation_state['day_trading']['is_active'] = False


# ============================================================================
# ML RETRAINING
# ============================================================================

def retrain_models_task():
    """Retrain models with all historical data."""
    global automation_state

    with state_lock:
        automation_state['ml_training']['status'] = 'running'
        automation_state['ml_training']['progress'] = 0
        automation_state['ml_training']['error'] = None

    try:
        print("🔄 Starting ML model retraining...")

        # Import training module
        import train_models

        # Run training
        with state_lock:
            automation_state['ml_training']['progress'] = 50

        # This will use the existing train_models.py
        # which already handles all historical data
        os.system('python train_models.py')

        with state_lock:
            automation_state['ml_training']['progress'] = 100
            automation_state['ml_training']['status'] = 'complete'
            automation_state['ml_training']['last_run'] = datetime.now(CST).isoformat()

        print("✅ Model retraining complete")

    except Exception as e:
        with state_lock:
            automation_state['ml_training']['status'] = 'error'
            automation_state['ml_training']['error'] = str(e)
        print(f"❌ Retraining error: {e}")


# ============================================================================
# DIGEST & EMAIL
# ============================================================================

def generate_digest():
    """Generate daily digest."""
    trades_today = load_json_file(TRADES_FILE, [])
    positions = load_json_file(POSITIONS_FILE, {})
    watchlist_data = load_json_file(WATCHLIST_FILE, {'symbols': []})

    total_trades = len(trades_today)
    buys = [t for t in trades_today if t['signal'] == 'BUY']
    sells = [t for t in trades_today if t['signal'] == 'SELL']

    total_pnl = sum(t.get('profit_loss', 0) for t in sells)
    winning_trades = sum(1 for t in sells if t.get('profit_loss', 0) > 0)
    losing_trades = sum(1 for t in sells if t.get('profit_loss', 0) < 0)
    win_rate = (winning_trades / len(sells) * 100) if sells else 0

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

    with open(DIGEST_FILE, 'w') as f:
        f.write(digest)

    return digest


def send_email_digest(recipient_email):
    """Send digest via email."""
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()

        digest_text = generate_digest()

        # Email configuration from .env
        sender_email = os.getenv('SMTP_USERNAME', '')
        sender_password = os.getenv('SMTP_PASSWORD', '')
        smtp_server = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.getenv('SMTP_PORT', '587'))

        if not sender_email or not sender_password:
            return False, "Email credentials not configured in .env file"

        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Day Trading Digest - {datetime.now(CST).strftime('%Y-%m-%d')}"

        msg.attach(MIMEText(digest_text, 'plain'))

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        return True, "Email sent successfully"

    except Exception as e:
        return False, str(e)


# ============================================================================
# FLASK ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main automation control panel."""
    return render_template('automation_control.html')


@app.route('/api/automation/status')
def get_automation_status():
    """Get current automation status."""
    with state_lock:
        status = automation_state.copy()

    # Add additional data
    watchlist_data = load_json_file(WATCHLIST_FILE, {'symbols': []})
    positions = load_json_file(POSITIONS_FILE, {})
    trades_today = load_json_file(TRADES_FILE, [])

    # Calculate statistics
    total_invested = sum(p['total_invested'] for p in positions.values())
    total_pnl_realized = sum(t.get('profit_loss', 0) for t in trades_today if 'profit_loss' in t)

    # Calculate unrealized P&L
    total_pnl_unrealized = 0
    position_details = []
    for symbol, pos in positions.items():
        current_price = get_current_price(symbol)
        if current_price:
            current_value = current_price * pos['shares']
            unrealized = current_value - pos['total_invested']
            unrealized_pct = (unrealized / pos['total_invested'] * 100) if pos['total_invested'] > 0 else 0
            total_pnl_unrealized += unrealized

            position_details.append({
                'symbol': symbol,
                'shares': round(pos['shares'], 2),
                'entry_price': round(pos['entry_price'], 2),
                'current_price': round(current_price, 2),
                'invested': round(pos['total_invested'], 2),
                'current_value': round(current_value, 2),
                'unrealized_pnl': round(unrealized, 2),
                'unrealized_pnl_pct': round(unrealized_pct, 2),
                'entry_time': pos.get('entry_time', '')
            })

    status['data'] = {
        'watchlist': watchlist_data.get('symbols', []),
        'watchlist_generated': watchlist_data.get('generated_at', None),
        'total_signals': watchlist_data.get('total_signals', 0),
        'positions': position_details,
        'total_invested': round(total_invested, 2),
        'total_pnl_realized': round(total_pnl_realized, 2),
        'total_pnl_unrealized': round(total_pnl_unrealized, 2),
        'total_pnl': round(total_pnl_realized + total_pnl_unrealized, 2),
        'trades_today': len(trades_today),
        'buys_today': sum(1 for t in trades_today if t['signal'] == 'BUY'),
        'sells_today': sum(1 for t in trades_today if t['signal'] == 'SELL')
    }

    return jsonify(status)


@app.route('/api/automation/generate-signals', methods=['POST'])
def trigger_signal_generation():
    """Manually trigger signal generation."""
    with state_lock:
        if automation_state['signal_generation']['status'] == 'running':
            return jsonify({'error': 'Signal generation already running'}), 400

    thread = threading.Thread(target=generate_signals_task)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/automation/start-trading', methods=['POST'])
def start_trading():
    """Start day trading automation."""
    global trading_thread_control

    with state_lock:
        if automation_state['day_trading']['is_active']:
            return jsonify({'error': 'Trading already active'}), 400

    trading_thread_control['running'] = True
    thread = threading.Thread(target=day_trading_loop)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/automation/stop-trading', methods=['POST'])
def stop_trading():
    """Stop day trading automation and close all positions."""
    global trading_thread_control

    trading_thread_control['running'] = False

    with state_lock:
        automation_state['day_trading']['status'] = 'stopped'
        automation_state['day_trading']['is_active'] = False

    # Close all open positions
    positions = load_json_file(POSITIONS_FILE, {})
    trades_today = load_json_file(TRADES_FILE, [])

    closed_count = 0
    total_pnl = 0

    if positions:
        print("\n🛑 Closing all positions...")
        for symbol, pos in list(positions.items()):
            try:
                current_price = get_current_price(symbol)
                if current_price is None:
                    print(f"  ⚠️ Could not get price for {symbol}, skipping")
                    continue

                # Calculate P&L
                entry_price = pos['entry_price']
                shares = pos['shares']
                invested = pos['invested']
                current_value = shares * current_price
                pnl = current_value - invested

                # Create sell trade
                trade = execute_trade(symbol, 'SELL', current_price, current_value)
                trade['pnl'] = round(pnl, 2)
                trade['pnl_pct'] = round((pnl / invested) * 100, 2) if invested > 0 else 0
                trades_today.append(trade)

                print(f"  ✅ Closed {symbol}: P&L = ${pnl:.2f} ({trade['pnl_pct']:.2f}%)")

                closed_count += 1
                total_pnl += pnl

            except Exception as e:
                print(f"  ❌ Error closing {symbol}: {e}")

        # Clear positions file
        save_json_file(POSITIONS_FILE, {})
        save_json_file(TRADES_FILE, trades_today)

        message = f"Trading stopped. Closed {closed_count} position(s) with total P&L of ${total_pnl:.2f}"
        print(f"\n✅ {message}\n")
    else:
        message = "Trading stopped. No positions to close."
        print(f"\n✅ {message}\n")

    return jsonify({
        'status': 'stopped',
        'message': message,
        'positions_closed': closed_count,
        'total_pnl': round(total_pnl, 2)
    })


@app.route('/api/automation/retrain', methods=['POST'])
def trigger_retraining():
    """Trigger ML model retraining."""
    with state_lock:
        if automation_state['ml_training']['status'] == 'running':
            return jsonify({'error': 'Training already running'}), 400

    thread = threading.Thread(target=retrain_models_task)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/automation/digest', methods=['GET'])
def get_digest():
    """Get current digest."""
    digest = generate_digest()
    return jsonify({'digest': digest})


@app.route('/api/automation/send-email', methods=['POST'])
def send_digest_email():
    """Send digest via email."""
    data = request.get_json() or {}
    recipient = data.get('email')

    if not recipient:
        return jsonify({'error': 'Email address required'}), 400

    success, message = send_email_digest(recipient)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 500


@app.route('/api/trades/history')
def get_trade_history():
    """Get trade history."""
    trades = load_json_file(TRADES_FILE, [])
    return jsonify({'trades': trades})


if __name__ == '__main__':
    print("=" * 70)
    print("Day Trading Automation Control Panel")
    print("=" * 70)
    print(f"Starting server at http://localhost:5002")
    print("=" * 70)
    app.run(debug=True, host='0.0.0.0', port=5002)
