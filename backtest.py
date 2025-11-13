import os
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import pickle
from features import build_features
import config

# =====================================================
# CONFIG
# =====================================================
BACKTEST_RESULTS_PATH = "data/backtest_results.csv"
PERFORMANCE_SUMMARY_PATH = "data/backtest_performance.txt"
CLF_PATH = config.CLF_PATH
REG_PATH = config.Q90_PATH

# =====================================================
# LOAD MODELS
# =====================================================
print("📦 Loading models...")
with open(CLF_PATH, "rb") as f:
    clf_pack = pickle.load(f)
with open(REG_PATH, "rb") as f:
    reg_pack = pickle.load(f)

clf = clf_pack["model"]
reg = reg_pack["model"]
print("✅ Models loaded")

# =====================================================
# BACKTESTING FUNCTIONS
# =====================================================
def fetch_historical_data(symbol, start_date, end_date):
    """Fetch historical price data for backtesting."""
    try:
        df = yf.download(
            symbol, 
            start=start_date, 
            end=end_date, 
            interval="1d", 
            progress=False,
            auto_adjust=True
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
        print(f"⚠️ Error fetching {symbol}: {e}")
        return None


def calculate_actual_return(symbol, entry_date, horizon_days=10):
    """Calculate the actual return over the prediction horizon."""
    try:
        # Fetch data from entry_date to horizon_days later
        start = entry_date
        end = entry_date + timedelta(days=horizon_days + 5)  # buffer for weekends
        
        df = yf.download(
            symbol,
            start=start,
            end=end,
            interval="1d",
            progress=False,
            auto_adjust=True
        )
        
        if df.empty or len(df) < 2:
            return None
        
        # Get entry price (first available) and exit price (after horizon_days trading days)
        entry_price = df['Close'].iloc[0]
        
        # Find price after horizon_days trading days
        if len(df) > horizon_days:
            exit_price = df['Close'].iloc[horizon_days]
        else:
            exit_price = df['Close'].iloc[-1]  # use last available if not enough days
        
        actual_return = (exit_price - entry_price) / entry_price
        return actual_return
        
    except Exception as e:
        print(f"⚠️ Could not calculate return for {symbol}: {e}")
        return None


def backtest_model(test_symbols, backtest_days=60):
    """
    Backtest the model on historical data.
    For each day in the past, generate predictions and track actual outcomes.
    """
    results = []
    
    # Define backtest period
    end_date = datetime.now() - timedelta(days=config.HORIZON_DAYS + 2)  # exclude recent days
    start_date = end_date - timedelta(days=backtest_days + 90)  # need extra days for features
    
    print(f"🔍 Backtesting from {start_date.date()} to {end_date.date()}")
    print(f"📊 Testing on {len(test_symbols)} symbols\n")
    
    for symbol in test_symbols:
        print(f"Testing {symbol}...", end=" ")
        
        # Fetch historical data
        df = fetch_historical_data(symbol, start_date, end_date + timedelta(days=30))
        if df is None or df.empty:
            print("❌ No data")
            continue
        
        # Build features
        feats = build_features(df)
        if feats is None or feats.empty:
            print("❌ No features")
            continue
        
        # Test on each day in the backtest period
        test_start = end_date - timedelta(days=backtest_days)
        test_dates = feats[
            (feats['date'] >= pd.Timestamp(test_start)) & 
            (feats['date'] <= pd.Timestamp(end_date))
        ]
        
        for idx, row in test_dates.iterrows():
            signal_date = pd.Timestamp(row['date'])
            
            # Prepare features
            X = feats[feats['date'] == signal_date].drop(
                columns=['future_return_10d', 'target_11pct', 'date', 'symbol'],
                errors='ignore'
            ).select_dtypes(include=[np.number])
            
            if X.empty:
                continue
            
            try:
                # Generate prediction
                prob = clf.predict_proba(X)[0, 1]
                pred_return = reg.predict(X)[0]
                
                # Only track signals that meet our threshold
                if prob >= config.TARGET_PRECISION:
                    # Calculate actual return
                    actual_return = calculate_actual_return(
                        symbol, 
                        signal_date.to_pydatetime(),
                        config.HORIZON_DAYS
                    )
                    
                    if actual_return is not None:
                        results.append({
                            'symbol': symbol,
                            'signal_date': signal_date.date(),
                            'entry_price': row['close'],
                            'predicted_prob': prob,
                            'predicted_return': pred_return,
                            'actual_return': actual_return,
                            'hit_target': actual_return >= config.TARGET_UPSIDE,
                            'days_tested': config.HORIZON_DAYS
                        })
            except Exception as e:
                print(f"⚠️ Prediction error: {e}")
                continue
        
        print(f"✅ {len([r for r in results if r['symbol'] == symbol])} signals")
    
    return pd.DataFrame(results)


# =====================================================
# PERFORMANCE METRICS
# =====================================================
def calculate_performance_metrics(df_results):
    """Calculate comprehensive performance metrics."""
    if df_results.empty:
        return None
    
    total_signals = len(df_results)
    winners = df_results[df_results['hit_target'] == True].shape[0]
    losers = total_signals - winners
    
    precision = winners / total_signals if total_signals > 0 else 0
    
    avg_return = df_results['actual_return'].mean()
    median_return = df_results['actual_return'].median()
    
    avg_winner = df_results[df_results['hit_target'] == True]['actual_return'].mean()
    avg_loser = df_results[df_results['hit_target'] == False]['actual_return'].mean()
    
    best_trade = df_results['actual_return'].max()
    worst_trade = df_results['actual_return'].min()
    
    # Model calibration: predicted prob vs actual hit rate
    df_results['prob_bucket'] = pd.cut(
        df_results['predicted_prob'],
        bins=[0.6, 0.7, 0.8, 0.9, 1.0],
        labels=['60-70%', '70-80%', '80-90%', '90-100%']
    )
    calibration = df_results.groupby('prob_bucket')['hit_target'].agg(['mean', 'count'])
    
    metrics = {
        'total_signals': total_signals,
        'winners': winners,
        'losers': losers,
        'precision': precision,
        'target_precision': config.TARGET_PRECISION,
        'avg_return': avg_return,
        'median_return': median_return,
        'avg_winner': avg_winner,
        'avg_loser': avg_loser,
        'best_trade': best_trade,
        'worst_trade': worst_trade,
        'calibration': calibration
    }
    
    return metrics


def print_performance_report(metrics, df_results):
    """Print and save a detailed performance report."""
    report = []
    report.append("=" * 70)
    report.append("BACKTEST PERFORMANCE REPORT")
    report.append("=" * 70)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Model: {CLF_PATH}")
    report.append(f"Target: {config.TARGET_UPSIDE * 100}% gain in {config.HORIZON_DAYS} days")
    report.append(f"Threshold: {config.TARGET_PRECISION * 100}% confidence\n")
    
    report.append("-" * 70)
    report.append("OVERALL RESULTS")
    report.append("-" * 70)
    report.append(f"Total Signals:        {metrics['total_signals']}")
    report.append(f"Winners (≥11%):       {metrics['winners']} ({metrics['winners']/metrics['total_signals']*100:.1f}%)")
    report.append(f"Losers (<11%):        {metrics['losers']} ({metrics['losers']/metrics['total_signals']*100:.1f}%)")
    report.append(f"\n✨ PRECISION:          {metrics['precision']*100:.1f}% (Target: {metrics['target_precision']*100:.0f}%)")
    
    status = "✅ BEATING TARGET" if metrics['precision'] >= metrics['target_precision'] else "⚠️ BELOW TARGET"
    report.append(f"Status:               {status}\n")
    
    report.append("-" * 70)
    report.append("RETURN STATISTICS")
    report.append("-" * 70)
    report.append(f"Average Return:       {metrics['avg_return']*100:+.2f}%")
    report.append(f"Median Return:        {metrics['median_return']*100:+.2f}%")
    report.append(f"Avg Winner:           {metrics['avg_winner']*100:+.2f}%")
    report.append(f"Avg Loser:            {metrics['avg_loser']*100:+.2f}%")
    report.append(f"Best Trade:           {metrics['best_trade']*100:+.2f}%")
    report.append(f"Worst Trade:          {metrics['worst_trade']*100:+.2f}%\n")
    
    report.append("-" * 70)
    report.append("MODEL CALIBRATION (Predicted Prob vs Actual Hit Rate)")
    report.append("-" * 70)
    for bucket, row in metrics['calibration'].iterrows():
        report.append(f"{bucket:10s}  →  {row['mean']*100:5.1f}% hit rate  ({int(row['count'])} signals)")
    
    report.append("\n" + "-" * 70)
    report.append("TOP 10 BEST TRADES")
    report.append("-" * 70)
    top_trades = df_results.nlargest(10, 'actual_return')[
        ['symbol', 'signal_date', 'predicted_prob', 'actual_return']
    ]
    for idx, row in top_trades.iterrows():
        report.append(
            f"{row['symbol']:6s} | {row['signal_date']} | "
            f"Pred: {row['predicted_prob']*100:5.1f}% | "
            f"Actual: {row['actual_return']*100:+6.2f}%"
        )
    
    report.append("\n" + "-" * 70)
    report.append("TOP 10 WORST TRADES")
    report.append("-" * 70)
    worst_trades = df_results.nsmallest(10, 'actual_return')[
        ['symbol', 'signal_date', 'predicted_prob', 'actual_return']
    ]
    for idx, row in worst_trades.iterrows():
        report.append(
            f"{row['symbol']:6s} | {row['signal_date']} | "
            f"Pred: {row['predicted_prob']*100:5.1f}% | "
            f"Actual: {row['actual_return']*100:+6.2f}%"
        )
    
    report.append("\n" + "=" * 70)
    
    # Print to console
    report_text = "\n".join(report)
    print(report_text)
    
    # Save to file
    with open(PERFORMANCE_SUMMARY_PATH, 'w') as f:
        f.write(report_text)
    
    print(f"\n💾 Performance report saved to {PERFORMANCE_SUMMARY_PATH}")


# =====================================================
# MAIN EXECUTION
# =====================================================
def run_backtest(test_symbols=None, backtest_days=60):
    """Run complete backtesting pipeline."""
    
    if test_symbols is None:
        # Use a diverse set of liquid stocks for testing
        test_symbols = [
            'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD',
            'NFLX', 'CRM', 'AVGO', 'INTC', 'CSCO', 'ORCL', 'ADBE', 'QCOM',
            'TXN', 'AMAT', 'MU', 'LRCX', 'KLAC', 'SNPS', 'CDNS', 'MRVL',
            'FTNT', 'PANW', 'CRWD', 'ZS', 'DDOG', 'NET', 'SNOW', 'MDB'
        ]
    
    print(f"🎯 Starting backtest with {len(test_symbols)} symbols")
    print(f"📅 Looking back {backtest_days} days\n")
    
    # Run backtest
    df_results = backtest_model(test_symbols, backtest_days)
    
    if df_results.empty:
        print("\n❌ No backtest results generated. Check data availability.")
        return
    
    # Save raw results
    df_results.to_csv(BACKTEST_RESULTS_PATH, index=False)
    print(f"\n💾 Raw results saved to {BACKTEST_RESULTS_PATH}")
    
    # Calculate and display metrics
    metrics = calculate_performance_metrics(df_results)
    print_performance_report(metrics, df_results)
    
    # Return results for further analysis
    return df_results, metrics


# =====================================================
# RUN IF CALLED DIRECTLY
# =====================================================
if __name__ == "__main__":
    print("🚀 Starting Backtest Module\n")
    df_results, metrics = run_backtest(backtest_days=60)
    
    if metrics:
        if metrics['precision'] >= config.TARGET_PRECISION:
            print("\n🎉 Model is performing at or above target precision!")
        else:
            print("\n⚠️ Model is underperforming. Consider retraining with more data.")
