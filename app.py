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
    'start_time': None
}

# Lock for thread-safe state updates
state_lock = threading.Lock()
day_trade_lock = threading.Lock()


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

def scan_day_trades_task(interval='5m', use_watchlist=False):
    """Background task to scan for day trading signals."""
    global day_trade_state

    with day_trade_lock:
        day_trade_state['status'] = 'running'
        day_trade_state['progress'] = 0
        day_trade_state['signals'] = []
        day_trade_state['error'] = None
        day_trade_state['start_time'] = time.time()

    try:
        # Get tickers
        if use_watchlist:
            tickers = get_watchlist_stocks()
        else:
            tickers = get_sp500_tickers()[:50]  # Top 50 for speed

        with day_trade_lock:
            day_trade_state['total'] = len(tickers)

        signals = []

        for i, symbol in enumerate(tickers):
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

                    for sig in stock_signals:
                        signals.append({
                            'symbol': symbol,
                            'signal': sig['type'],
                            'indicator': sig['indicator'],
                            'reason': sig['reason'],
                            'strength': sig['strength'],
                            'price': round(float(latest['close']), 2),
                            'vwap': round(float(latest['vwap']), 2),
                            'rsi': round(float(latest['rsi']), 1),
                            'volume_ratio': round(float(latest['relative_volume']), 2)
                        })

            except Exception as e:
                continue

            # Rate limiting
            if i > 0 and i % 10 == 0:
                time.sleep(0.5)

        # Sort by strength
        strength_order = {'High': 3, 'Medium': 2, 'Low': 1}
        signals.sort(key=lambda x: (strength_order.get(x['strength'], 0), x['signal'] == 'BUY'), reverse=True)

        with day_trade_lock:
            day_trade_state['status'] = 'complete'
            day_trade_state['signals'] = signals
            day_trade_state['last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            day_trade_state['current_ticker'] = ''

    except Exception as e:
        with day_trade_lock:
            day_trade_state['status'] = 'error'
            day_trade_state['error'] = str(e)


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


@app.route('/api/daytrading/scan', methods=['POST'])
def api_daytrading_scan():
    """Start day trading scan."""
    global day_trade_state

    with day_trade_lock:
        if day_trade_state['status'] == 'running':
            return jsonify({'error': 'Scan already in progress'}), 400

    # Get parameters
    data = request.get_json() or {}
    interval = data.get('interval', '5m')
    use_watchlist = data.get('watchlist', False)

    # Start background task
    thread = threading.Thread(target=scan_day_trades_task, args=(interval, use_watchlist))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started'})


@app.route('/api/daytrading/status')
def api_daytrading_status():
    """Get day trading scan status."""
    with day_trade_lock:
        elapsed = 0
        if day_trade_state['start_time'] and day_trade_state['status'] == 'running':
            elapsed = int(time.time() - day_trade_state['start_time'])

        return jsonify({
            'status': day_trade_state['status'],
            'progress': day_trade_state['progress'],
            'total': day_trade_state['total'],
            'current_ticker': day_trade_state['current_ticker'],
            'signals': day_trade_state['signals'],
            'error': day_trade_state['error'],
            'last_run': day_trade_state['last_run'],
            'elapsed_seconds': elapsed
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
