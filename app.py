"""
Stock Sentiment Agent - Web UI
Flask application for running signal generation on demand
"""
import os
import pickle
import threading
import time
from datetime import datetime
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np

# Import project modules
import config
from features import build_features
from symbols import get_sp500_tickers
from utils import is_valid_stock
from intraday_features import build_intraday_features, generate_day_trading_signals, get_market_status
from day_trading_scanner import get_watchlist_stocks

app = Flask(__name__)

# Global state for signal generation
signal_state = {
    'status': 'idle',  # idle, running, complete, error
    'progress': 0,
    'total': 0,
    'current_ticker': '',
    'signals': [],
    'error': None,
    'last_run': None,
    'start_time': None
}

# Global state for day trading
day_trade_state = {
    'status': 'idle',
    'progress': 0,
    'total': 0,
    'current_ticker': '',
    'signals': [],
    'error': None,
    'last_run': None,
    'start_time': None,
    'watchlist': [],  # User's custom watchlist
    'scanning': False,  # Continuous scanning flag
    'scan_interval': 60,  # Scan every 60 seconds
    'signal_history': []  # Track all signals
}

# Lock for thread-safe state updates
state_lock = threading.Lock()
day_trade_lock = threading.Lock()

# Continuous scanning control
scan_control = {'running': False}


def fetch_data(symbol, period="3mo", interval="1d"):
    """Fetch price data for a single ticker."""
    import yfinance as yf
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            progress=False,
            auto_adjust=True,
            timeout=30
        )
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


def load_models():
    """Load trained models."""
    try:
        with open(config.CLF_PATH, "rb") as f:
            clf_pack = pickle.load(f)
        with open(config.Q90_PATH, "rb") as f:
            reg_pack = pickle.load(f)
        return clf_pack, reg_pack
    except FileNotFoundError:
        return None, None


def generate_signals_task():
    """Background task to generate signals."""
    global signal_state

    with state_lock:
        signal_state['status'] = 'running'
        signal_state['progress'] = 0
        signal_state['signals'] = []
        signal_state['error'] = None
        signal_state['start_time'] = time.time()

    try:
        # Load models
        clf_pack, reg_pack = load_models()
        if clf_pack is None:
            with state_lock:
                signal_state['status'] = 'error'
                signal_state['error'] = 'Models not found. Please train models first.'
            return

        clf = clf_pack['model']
        reg = reg_pack['model']
        model_features = clf_pack['features']

        # Get tickers
        tickers = get_sp500_tickers()

        with state_lock:
            signal_state['total'] = len(tickers)

        signals = []
        MIN_VOLUME = 100000
        PREDICTION_THRESHOLD = config.CONFIDENCE_TIERS.get('medium', 0.60)

        for i, sym in enumerate(tickers):
            with state_lock:
                signal_state['progress'] = i + 1
                signal_state['current_ticker'] = sym

            # Fetch data
            df = fetch_data(sym)
            if df is None:
                continue

            # Build features (no sentiment to match model)
            feats = build_features(df, symbol=sym, include_sentiment=False)
            if feats is None or feats.empty:
                continue

            # Validate stock (not ETF, etc.)
            try:
                validation = is_valid_stock(sym, min_volume=MIN_VOLUME)
                if not validation['is_valid']:
                    continue
            except:
                pass  # Skip validation if it fails

            # Prepare features for prediction
            drop_cols = ["future_return_10d", "target_hit", "date", "symbol"]
            X = feats.drop(columns=drop_cols, errors="ignore")
            X = X.select_dtypes(include=[np.number])

            # Align features with model
            for col in model_features:
                if col not in X.columns:
                    X[col] = 0
            X = X[model_features]

            # Get last row for prediction
            X_last = X.iloc[-1:]

            try:
                proba = clf.predict_proba(X_last)[0, 1]
                pred_return = reg.predict(X_last)[0]

                if proba >= PREDICTION_THRESHOLD:
                    latest_close = float(df['close'].iloc[-1])
                    signals.append({
                        'symbol': sym,
                        'probability': round(proba * 100, 1),
                        'predicted_return': round(pred_return * 100, 2),
                        'price': round(latest_close, 2),
                        'confidence': 'High' if proba >= 0.70 else 'Medium' if proba >= 0.60 else 'Low'
                    })
            except Exception as e:
                continue

            # Small delay to avoid rate limiting
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

        # Sort by probability
        signals.sort(key=lambda x: x['probability'], reverse=True)

        with state_lock:
            signal_state['status'] = 'complete'
            signal_state['signals'] = signals
            signal_state['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            signal_state['current_ticker'] = ''

    except Exception as e:
        with state_lock:
            signal_state['status'] = 'error'
            signal_state['error'] = str(e)


def load_cached_signals():
    """Load signals from cached CSV file."""
    try:
        csv_path = os.path.join(config.DATA_DIR, 'daily_signals.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            signals = []
            for _, row in df.iterrows():
                signals.append({
                    'symbol': row['symbol'],
                    'probability': round(row['prob_11pct_up'] * 100, 1),
                    'predicted_return': round(row['predicted_return_q90'], 2),
                    'price': round(row['latest_close'], 2),
                    'confidence': 'High' if row['prob_11pct_up'] >= 0.70 else 'Medium'
                })
            return signals, df['date'].iloc[0] if len(df) > 0 else None
    except:
        pass
    return [], None


@app.route('/')
def index():
    """Main page."""
    # Load cached signals if available
    cached_signals, cached_date = load_cached_signals()

    # Check model status
    clf_exists = os.path.exists(config.CLF_PATH)
    reg_exists = os.path.exists(config.Q90_PATH)
    models_ready = clf_exists and reg_exists

    return render_template('index.html',
                         cached_signals=cached_signals,
                         cached_date=cached_date,
                         models_ready=models_ready,
                         config=config)


@app.route('/api/generate', methods=['POST'])
def api_generate():
    """Start signal generation."""
    global signal_state

    with state_lock:
        if signal_state['status'] == 'running':
            return jsonify({'error': 'Signal generation already in progress'}), 400

    # Start background task
    thread = threading.Thread(target=generate_signals_task)
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/status')
def api_status():
    """Get current status of signal generation."""
    with state_lock:
        elapsed = 0
        if signal_state['start_time'] and signal_state['status'] == 'running':
            elapsed = int(time.time() - signal_state['start_time'])

        return jsonify({
            'status': signal_state['status'],
            'progress': signal_state['progress'],
            'total': signal_state['total'],
            'current_ticker': signal_state['current_ticker'],
            'signals': signal_state['signals'],
            'error': signal_state['error'],
            'last_run': signal_state['last_run'],
            'elapsed_seconds': elapsed
        })


@app.route('/api/signals')
def api_signals():
    """Get generated signals."""
    with state_lock:
        return jsonify({
            'signals': signal_state['signals'],
            'last_run': signal_state['last_run']
        })


@app.route('/api/cached')
def api_cached():
    """Get cached signals from CSV."""
    signals, date = load_cached_signals()
    return jsonify({
        'signals': signals,
        'date': date
    })


# ============================================================================
# DAY TRADING ROUTES
# ============================================================================

def calculate_entry_exit_levels(df, signal_type):
    """Calculate entry, stop loss, and target prices."""
    latest = df.iloc[-1]
    price = float(latest['close'])
    atr = float(latest['high'] - latest['low'])  # Simple ATR
    vwap = float(latest['vwap'])

    if signal_type == 'BUY':
        # Entry slightly above current price
        entry = round(price * 1.002, 2)  # 0.2% above
        # Stop below recent low or below VWAP
        stop = round(min(price - (atr * 1.5), vwap * 0.995), 2)
        # Target based on ATR or resistance
        target = round(price + (atr * 2), 2)
    else:  # SELL
        entry = round(price * 0.998, 2)  # 0.2% below
        stop = round(max(price + (atr * 1.5), vwap * 1.005), 2)
        target = round(price - (atr * 2), 2)

    risk = abs(entry - stop)
    reward = abs(target - entry)
    risk_reward = round(reward / risk, 2) if risk > 0 else 0

    return {
        'entry': entry,
        'stop': stop,
        'target': target,
        'risk': round(risk, 2),
        'reward': round(reward, 2),
        'risk_reward': risk_reward
    }


def scan_day_trades_task(interval='5m', use_watchlist=False, continuous=False):
    """Background task to scan for day trading signals."""
    global day_trade_state, scan_control

    with day_trade_lock:
        day_trade_state['status'] = 'running'
        day_trade_state['progress'] = 0
        day_trade_state['error'] = None
        day_trade_state['start_time'] = time.time()
        if continuous:
            day_trade_state['scanning'] = True
            scan_control['running'] = True

    try:
        while True:
            # Get tickers from custom watchlist
            with day_trade_lock:
                tickers = day_trade_state['watchlist'].copy()
                if not tickers:
                    tickers = ['AAPL', 'TSLA', 'NVDA', 'AMD', 'META']  # Default
                day_trade_state['total'] = len(tickers)
                scan_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            signals = []

            for i, symbol in enumerate(tickers):
                # Check if we should stop
                if continuous and not scan_control['running']:
                    break

                with day_trade_lock:
                    day_trade_state['progress'] = i + 1
                    day_trade_state['current_ticker'] = symbol

                try:
                    # Build intraday features
                    df = build_intraday_features(symbol, interval=interval, days_back=2)

                    if df is None or df.empty:
                        continue

                    # Generate signals
                    stock_signals = generate_day_trading_signals(df)

                    if stock_signals:
                        latest = df.iloc[-1]

                        # Get candlestick data (last 20 periods)
                        candle_data = df.tail(20)[['timestamp', 'open', 'high', 'low', 'close', 'volume']].to_dict('records')

                        for sig in stock_signals:
                            # Calculate entry/exit levels
                            levels = calculate_entry_exit_levels(df, sig['type'])

                            signal_obj = {
                                'symbol': symbol,
                                'signal': sig['type'],
                                'indicator': sig['indicator'],
                                'reason': sig['reason'],
                                'strength': sig['strength'],
                                'price': round(float(latest['close']), 2),
                                'vwap': round(float(latest['vwap']), 2),
                                'rsi': round(float(latest['rsi']), 1),
                                'volume_ratio': round(float(latest['relative_volume']), 2),
                                'entry': levels['entry'],
                                'stop': levels['stop'],
                                'target': levels['target'],
                                'risk_reward': levels['risk_reward'],
                                'timestamp': scan_time,
                                'candlestick_data': candle_data
                            }
                            signals.append(signal_obj)

                            # Add to signal history
                            with day_trade_lock:
                                day_trade_state['signal_history'].append(signal_obj)
                                # Keep only last 100 signals
                                if len(day_trade_state['signal_history']) > 100:
                                    day_trade_state['signal_history'] = day_trade_state['signal_history'][-100:]

                except Exception as e:
                    continue

                # Small delay between stocks
                time.sleep(0.3)

            # Sort by strength
            strength_order = {'High': 3, 'Medium': 2, 'Low': 1}
            signals.sort(key=lambda x: (strength_order.get(x['strength'], 0), x['signal'] == 'BUY'), reverse=True)

            with day_trade_lock:
                day_trade_state['signals'] = signals
                day_trade_state['last_run'] = scan_time
                day_trade_state['current_ticker'] = ''

                if continuous and scan_control['running']:
                    day_trade_state['status'] = 'scanning'
                else:
                    day_trade_state['status'] = 'complete'

            # If continuous scanning, wait before next scan
            if continuous and scan_control['running']:
                time.sleep(day_trade_state['scan_interval'])
            else:
                break  # Single scan complete

    except Exception as e:
        with day_trade_lock:
            day_trade_state['status'] = 'error'
            day_trade_state['error'] = str(e)
            day_trade_state['scanning'] = False
        scan_control['running'] = False


@app.route('/daytrading')
def daytrading():
    """Day trading page."""
    # Get market status
    market = get_market_status()

    # Load cached signals if available
    cached_signals = []
    cached_date = None
    try:
        csv_path = os.path.join(config.DATA_DIR, 'day_trading_signals.csv')
        if os.path.exists(csv_path):
            df = pd.read_csv(csv_path)
            cached_signals = df.to_dict('records')
            if len(df) > 0 and 'timestamp' in df.columns:
                cached_date = df['timestamp'].iloc[0]
    except:
        pass

    return render_template('daytrading.html',
                         market_status=market,
                         cached_signals=cached_signals,
                         cached_date=cached_date)


@app.route('/api/daytrading/watchlist', methods=['GET'])
def api_get_watchlist():
    """Get custom watchlist."""
    with day_trade_lock:
        return jsonify({'watchlist': day_trade_state['watchlist']})


@app.route('/api/daytrading/watchlist/add', methods=['POST'])
def api_add_to_watchlist():
    """Add ticker to watchlist."""
    data = request.get_json() or {}
    symbol = data.get('symbol', '').upper().strip()

    if not symbol:
        return jsonify({'error': 'Symbol required'}), 400

    with day_trade_lock:
        if symbol not in day_trade_state['watchlist']:
            if len(day_trade_state['watchlist']) >= 10:
                return jsonify({'error': 'Watchlist limit (10 stocks) reached'}), 400
            day_trade_state['watchlist'].append(symbol)

    return jsonify({'success': True, 'watchlist': day_trade_state['watchlist']})


@app.route('/api/daytrading/watchlist/remove', methods=['POST'])
def api_remove_from_watchlist():
    """Remove ticker from watchlist."""
    data = request.get_json() or {}
    symbol = data.get('symbol', '').upper().strip()

    with day_trade_lock:
        if symbol in day_trade_state['watchlist']:
            day_trade_state['watchlist'].remove(symbol)

    return jsonify({'success': True, 'watchlist': day_trade_state['watchlist']})


@app.route('/api/daytrading/scan/start', methods=['POST'])
def api_start_continuous_scan():
    """Start continuous scanning."""
    global scan_control

    with day_trade_lock:
        if day_trade_state['scanning']:
            return jsonify({'error': 'Already scanning'}), 400

    # Get parameters
    data = request.get_json() or {}
    interval = data.get('interval', '5m')
    scan_frequency = data.get('frequency', 60)  # seconds

    with day_trade_lock:
        day_trade_state['scan_interval'] = scan_frequency

    # Start background task
    thread = threading.Thread(target=scan_day_trades_task, args=(interval, False, True))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'scanning': True})


@app.route('/api/daytrading/scan/stop', methods=['POST'])
def api_stop_continuous_scan():
    """Stop continuous scanning."""
    global scan_control

    scan_control['running'] = False

    with day_trade_lock:
        day_trade_state['scanning'] = False
        day_trade_state['status'] = 'idle'

    return jsonify({'status': 'stopped', 'scanning': False})


@app.route('/api/daytrading/history', methods=['GET'])
def api_signal_history():
    """Get signal history."""
    with day_trade_lock:
        return jsonify({'history': day_trade_state['signal_history']})


@app.route('/api/daytrading/status')
def api_daytrading_status():
    """Get day trading scan status."""
    with day_trade_lock:
        elapsed = 0
        if day_trade_state['start_time'] and day_trade_state['status'] in ['running', 'scanning']:
            elapsed = int(time.time() - day_trade_state['start_time'])

        return jsonify({
            'status': day_trade_state['status'],
            'progress': day_trade_state['progress'],
            'total': day_trade_state['total'],
            'current_ticker': day_trade_state['current_ticker'],
            'signals': day_trade_state['signals'],
            'error': day_trade_state['error'],
            'last_run': day_trade_state['last_run'],
            'elapsed_seconds': elapsed,
            'scanning': day_trade_state['scanning'],
            'watchlist': day_trade_state['watchlist'],
            'scan_interval': day_trade_state['scan_interval']
        })


@app.route('/api/daytrading/market')
def api_market_status():
    """Get market status."""
    market = get_market_status()
    return jsonify(market)


if __name__ == '__main__':
    print("=" * 60)
    print("Stock Sentiment Agent - Web UI")
    print("=" * 60)
    print(f"Models: {config.CLF_PATH}")
    print(f"Target: {config.TARGET_UPSIDE * 100}% in {config.HORIZON_DAYS} days")
    print(f"Threshold: {config.CONFIDENCE_TIERS.get('medium', 0.60) * 100}%")
    print("=" * 60)
    print("Starting server at http://localhost:5001")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5001)
