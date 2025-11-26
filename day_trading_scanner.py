"""
Day Trading Scanner
Scans stocks for intraday trading opportunities using VWAP, RSI, MACD, etc.
"""
import pandas as pd
import numpy as np
from datetime import datetime
import time
from intraday_features import (
    build_intraday_features,
    generate_day_trading_signals,
    get_market_status
)
from symbols import get_sp500_tickers
import config


def scan_for_day_trades(tickers=None, interval="5m", max_stocks=50):
    """
    Scan stocks for day trading opportunities.

    Args:
        tickers: List of tickers to scan (default: top S&P 500)
        interval: Time interval (1m, 5m, 15m)
        max_stocks: Maximum number of stocks to scan

    Returns:
        DataFrame with signals
    """
    if tickers is None:
        # Get S&P 500 stocks
        all_tickers = get_sp500_tickers()
        # Focus on most liquid stocks (first 50)
        tickers = all_tickers[:max_stocks]

    print(f"🔍 Scanning {len(tickers)} stocks for day trading opportunities...")
    print(f"   Interval: {interval}")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check market status
    market = get_market_status()
    print(f"   Market: {market['status']} - {market['message']}")
    print()

    results = []
    processed = 0

    for i, symbol in enumerate(tickers):
        try:
            # Fetch and analyze
            df = build_intraday_features(symbol, interval=interval, days_back=2)

            if df is None or df.empty:
                continue

            # Generate signals
            signals = generate_day_trading_signals(df)

            if signals:
                latest = df.iloc[-1]

                for signal in signals:
                    results.append({
                        'symbol': symbol,
                        'signal': signal['type'],
                        'indicator': signal['indicator'],
                        'reason': signal['reason'],
                        'strength': signal['strength'],
                        'price': round(latest['close'], 2),
                        'vwap': round(latest['vwap'], 2),
                        'rsi': round(latest['rsi'], 1),
                        'volume_ratio': round(latest['relative_volume'], 2),
                        'timestamp': latest['timestamp']
                    })

            processed += 1

            # Progress update
            if (i + 1) % 10 == 0:
                print(f"   Processed {i + 1}/{len(tickers)} stocks... ({len(results)} signals)")

            # Rate limiting
            if i > 0 and i % 10 == 0:
                time.sleep(1)

        except Exception as e:
            continue

    print(f"\n✅ Scan complete: {processed} stocks analyzed, {len(results)} signals found\n")

    if results:
        df_results = pd.DataFrame(results)

        # Sort by signal strength and indicator
        strength_order = {'High': 3, 'Medium': 2, 'Low': 1}
        df_results['strength_score'] = df_results['strength'].map(strength_order)
        df_results = df_results.sort_values(by=['strength_score', 'signal'], ascending=[False, False])
        df_results = df_results.drop(columns=['strength_score'])

        return df_results
    else:
        return pd.DataFrame()


def get_watchlist_stocks():
    """
    Get a curated watchlist of high-volume, volatile stocks for day trading.

    Returns:
        List of ticker symbols
    """
    # Popular day trading stocks (high volume, high volatility)
    watchlist = [
        # Tech mega-caps
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'TSLA',

        # High volatility tech
        'AMD', 'PLTR', 'SOFI', 'SNAP', 'COIN', 'RIOT', 'MARA',

        # Meme stocks
        'GME', 'AMC', 'BB', 'BBBY',

        # SPY and QQQ (ETFs for market direction)
        'SPY', 'QQQ', 'IWM',

        # Popular day trading stocks
        'NFLX', 'UBER', 'LYFT', 'ABNB', 'HOOD', 'F', 'NIO',
        'BABA', 'PDD', 'JD', 'ZM', 'SHOP', 'SQ', 'PYPL'
    ]

    return watchlist


def monitor_positions(symbols, interval="5m", check_interval=60):
    """
    Monitor open positions in real-time.

    Args:
        symbols: List of ticker symbols to monitor
        interval: Data interval
        check_interval: How often to check (seconds)
    """
    print(f"👀 Monitoring {len(symbols)} positions...")
    print(f"   Check interval: {check_interval} seconds")
    print()

    try:
        while True:
            print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')} - Checking positions...")

            for symbol in symbols:
                try:
                    df = build_intraday_features(symbol, interval=interval, days_back=1)

                    if df is None or df.empty:
                        continue

                    latest = df.iloc[-1]
                    signals = generate_day_trading_signals(df)

                    # Display current status
                    vwap_status = "above" if latest['close'] > latest['vwap'] else "below"
                    rsi_status = "overbought" if latest['rsi'] > 70 else "oversold" if latest['rsi'] < 30 else "neutral"

                    print(f"\n{symbol}:")
                    print(f"  Price: ${latest['close']:.2f} ({vwap_status} VWAP ${latest['vwap']:.2f})")
                    print(f"  RSI: {latest['rsi']:.1f} ({rsi_status})")
                    print(f"  Volume: {latest['relative_volume']:.2f}x average")

                    if signals:
                        print(f"  🚨 SIGNALS:")
                        for sig in signals:
                            print(f"    {sig['type']:4} | {sig['indicator']:15} | {sig['reason']}")

                except Exception as e:
                    print(f"  Error monitoring {symbol}: {e}")

            print(f"\n⏸️  Waiting {check_interval} seconds...")
            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n\n👋 Monitoring stopped")


def save_signals_to_csv(df, filename="data/day_trading_signals.csv"):
    """Save day trading signals to CSV."""
    if df is not None and not df.empty:
        df.to_csv(filename, index=False)
        print(f"💾 Signals saved to {filename}")
        return True
    return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Day Trading Scanner')
    parser.add_argument('--mode', choices=['scan', 'monitor', 'watchlist'],
                       default='scan', help='Operation mode')
    parser.add_argument('--interval', default='5m',
                       help='Time interval (1m, 5m, 15m)')
    parser.add_argument('--stocks', type=int, default=50,
                       help='Number of stocks to scan')
    parser.add_argument('--symbols', nargs='+',
                       help='Specific symbols to monitor')

    args = parser.parse_args()

    if args.mode == 'scan':
        # Scan for signals
        tickers = args.symbols if args.symbols else None
        df = scan_for_day_trades(tickers=tickers, interval=args.interval, max_stocks=args.stocks)

        if not df.empty:
            print("=" * 80)
            print("DAY TRADING SIGNALS")
            print("=" * 80)
            print(df.to_string(index=False))
            print()

            # Save to CSV
            save_signals_to_csv(df)

            # Summary by signal type
            print("\nSummary:")
            print(f"  BUY signals:  {len(df[df['signal'] == 'BUY'])}")
            print(f"  SELL signals: {len(df[df['signal'] == 'SELL'])}")
        else:
            print("⚠️  No signals found at this time")

    elif args.mode == 'watchlist':
        # Scan watchlist
        watchlist = get_watchlist_stocks()
        print(f"📋 Watchlist ({len(watchlist)} stocks):")
        print(f"   {', '.join(watchlist)}")
        print()

        df = scan_for_day_trades(tickers=watchlist, interval=args.interval, max_stocks=len(watchlist))

        if not df.empty:
            print("=" * 80)
            print("WATCHLIST SIGNALS")
            print("=" * 80)
            print(df.to_string(index=False))
            save_signals_to_csv(df)
        else:
            print("⚠️  No signals on watchlist")

    elif args.mode == 'monitor':
        # Monitor positions
        if not args.symbols:
            print("Error: --symbols required for monitor mode")
            print("Example: python day_trading_scanner.py --mode monitor --symbols AAPL TSLA NVDA")
            return

        monitor_positions(args.symbols, interval=args.interval)


if __name__ == "__main__":
    main()
