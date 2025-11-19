"""Utility functions for stock validation and filtering."""

import yfinance as yf
from typing import Dict, Optional


def is_valid_stock(symbol: str, min_volume: int = 100000) -> Dict[str, any]:
    """
    Check if a ticker is a valid, tradeable stock (not ETF, mutual fund, etc.).

    Args:
        symbol: Stock ticker symbol
        min_volume: Minimum average daily volume threshold

    Returns:
        Dict with validation results:
        {
            'is_valid': bool,
            'reason': str,
            'quote_type': str,
            'avg_volume': int
        }
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if not info or len(info) <= 1:
            return {
                'is_valid': False,
                'reason': 'No data available',
                'quote_type': None,
                'avg_volume': 0
            }

        quote_type = info.get('quoteType', '').upper()

        # Filter out non-stocks
        invalid_types = ['ETF', 'MUTUALFUND', 'INDEX', 'CURRENCY', 'CRYPTOCURRENCY']
        if quote_type in invalid_types:
            return {
                'is_valid': False,
                'reason': f'Not a stock (type: {quote_type})',
                'quote_type': quote_type,
                'avg_volume': info.get('averageVolume', 0)
            }

        # Check if it's actually equity
        if quote_type != 'EQUITY':
            # Some stocks may not have quoteType, check for other indicators
            if 'regularMarketPrice' not in info and 'currentPrice' not in info:
                return {
                    'is_valid': False,
                    'reason': 'No price data available',
                    'quote_type': quote_type,
                    'avg_volume': 0
                }

        # Check volume (liquidity filter)
        avg_volume = info.get('averageVolume', 0) or info.get('averageDailyVolume10Day', 0)
        if avg_volume < min_volume:
            return {
                'is_valid': False,
                'reason': f'Low volume ({avg_volume:,} < {min_volume:,})',
                'quote_type': quote_type,
                'avg_volume': avg_volume
            }

        # Check if delisted or has other issues
        market_state = info.get('marketState', '')
        if market_state == 'CLOSED' and info.get('regularMarketPrice') is None:
            return {
                'is_valid': False,
                'reason': 'Possibly delisted',
                'quote_type': quote_type,
                'avg_volume': avg_volume
            }

        return {
            'is_valid': True,
            'reason': 'Valid stock',
            'quote_type': quote_type,
            'avg_volume': avg_volume
        }

    except Exception as e:
        return {
            'is_valid': False,
            'reason': f'Error: {str(e)}',
            'quote_type': None,
            'avg_volume': 0
        }


def validate_ticker_batch(symbols: list, min_volume: int = 100000, max_workers: int = 10) -> Dict[str, Dict]:
    """
    Validate multiple tickers in parallel.

    Args:
        symbols: List of ticker symbols to validate
        min_volume: Minimum average daily volume
        max_workers: Number of parallel workers

    Returns:
        Dict mapping symbol -> validation result
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {
            executor.submit(is_valid_stock, symbol, min_volume): symbol
            for symbol in symbols
        }

        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                results[symbol] = future.result()
            except Exception as e:
                results[symbol] = {
                    'is_valid': False,
                    'reason': f'Validation error: {str(e)}',
                    'quote_type': None,
                    'avg_volume': 0
                }

    return results
