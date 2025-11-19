"""
Sentiment analysis module for stock news and social media.
Provides sentiment scores that can be used as model features.
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import re


def get_news_sentiment(symbol: str, lookback_days: int = 7) -> Dict[str, float]:
    """
    Get sentiment scores from recent news for a given stock.

    Uses Yahoo Finance news headlines and applies basic sentiment analysis.

    Args:
        symbol: Stock ticker symbol
        lookback_days: Number of days to look back for news

    Returns:
        Dict with sentiment metrics:
        {
            'news_count': int,
            'sentiment_score': float (-1 to +1),
            'sentiment_positive': float (0 to 1),
            'sentiment_negative': float (0 to 1),
            'sentiment_neutral': float (0 to 1)
        }
    """
    try:
        ticker = yf.Ticker(symbol)
        news = ticker.news

        if not news or len(news) == 0:
            return {
                'news_count': 0,
                'sentiment_score': 0.0,
                'sentiment_positive': 0.0,
                'sentiment_negative': 0.0,
                'sentiment_neutral': 1.0
            }

        # Filter news by date (if timestamp available)
        cutoff_time = datetime.now() - timedelta(days=lookback_days)
        recent_news = []

        for item in news:
            # Check if news is recent (some APIs don't provide timestamps)
            if 'providerPublishTime' in item:
                pub_time = datetime.fromtimestamp(item['providerPublishTime'])
                if pub_time >= cutoff_time:
                    recent_news.append(item)
            else:
                # If no timestamp, include it (assume recent)
                recent_news.append(item)

        if len(recent_news) == 0:
            recent_news = news[:10]  # Use most recent 10 if no date filter works

        # Analyze sentiment of headlines
        sentiments = []
        for item in recent_news:
            title = item.get('title', '')
            if title:
                sent = analyze_text_sentiment(title)
                sentiments.append(sent)

        if len(sentiments) == 0:
            return {
                'news_count': 0,
                'sentiment_score': 0.0,
                'sentiment_positive': 0.0,
                'sentiment_negative': 0.0,
                'sentiment_neutral': 1.0
            }

        # Aggregate sentiments
        avg_score = sum(s['score'] for s in sentiments) / len(sentiments)
        pct_positive = sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments)
        pct_negative = sum(1 for s in sentiments if s['label'] == 'negative') / len(sentiments)
        pct_neutral = sum(1 for s in sentiments if s['label'] == 'neutral') / len(sentiments)

        return {
            'news_count': len(recent_news),
            'sentiment_score': round(avg_score, 3),
            'sentiment_positive': round(pct_positive, 3),
            'sentiment_negative': round(pct_negative, 3),
            'sentiment_neutral': round(pct_neutral, 3)
        }

    except Exception as e:
        # Return neutral sentiment on error
        return {
            'news_count': 0,
            'sentiment_score': 0.0,
            'sentiment_positive': 0.0,
            'sentiment_negative': 0.0,
            'sentiment_neutral': 1.0
        }


def analyze_text_sentiment(text: str) -> Dict[str, any]:
    """
    Perform basic sentiment analysis on text using keyword matching.

    This is a simple rule-based approach. For production, consider using:
    - TextBlob
    - VADER (vaderSentiment)
    - Transformers (FinBERT for financial text)

    Args:
        text: Text to analyze

    Returns:
        Dict with 'score' (-1 to +1) and 'label' (positive/negative/neutral)
    """
    text_lower = text.lower()

    # Financial sentiment keywords
    positive_keywords = [
        'surge', 'soar', 'rally', 'gain', 'jump', 'climb', 'rise', 'up',
        'beat', 'exceed', 'outperform', 'strong', 'growth', 'profit',
        'bullish', 'upgrade', 'buy', 'positive', 'optimistic', 'record',
        'breakthrough', 'innovative', 'success', 'expansion', 'boost',
        'revenue', 'earnings beat', 'higher', 'increased', 'improve'
    ]

    negative_keywords = [
        'plunge', 'plummet', 'crash', 'fall', 'drop', 'decline', 'down',
        'miss', 'disappoint', 'underperform', 'weak', 'loss', 'losses',
        'bearish', 'downgrade', 'sell', 'negative', 'pessimistic', 'concern',
        'risk', 'warning', 'lawsuit', 'investigation', 'scandal', 'cut',
        'lower', 'decreased', 'worsen', 'fail', 'debt', 'layoff'
    ]

    # Count matches
    pos_count = sum(1 for keyword in positive_keywords if keyword in text_lower)
    neg_count = sum(1 for keyword in negative_keywords if keyword in text_lower)

    # Calculate score
    total = pos_count + neg_count
    if total == 0:
        score = 0.0
        label = 'neutral'
    else:
        score = (pos_count - neg_count) / total
        if score > 0.2:
            label = 'positive'
        elif score < -0.2:
            label = 'negative'
        else:
            label = 'neutral'

    return {
        'score': score,
        'label': label,
        'pos_keywords': pos_count,
        'neg_keywords': neg_count
    }


def get_batch_sentiment(symbols: List[str], lookback_days: int = 7) -> Dict[str, Dict]:
    """
    Get sentiment for multiple symbols.

    Args:
        symbols: List of ticker symbols
        lookback_days: Days to look back for news

    Returns:
        Dict mapping symbol -> sentiment metrics
    """
    results = {}

    for symbol in symbols:
        results[symbol] = get_news_sentiment(symbol, lookback_days)

    return results


# =====================================================
# ADVANCED: Optional FinBERT Integration
# =====================================================
def get_finbert_sentiment(text: str) -> Dict[str, any]:
    """
    Use FinBERT (Financial BERT) for more accurate sentiment analysis.

    Requires: pip install transformers torch

    This is commented out by default to avoid heavy dependencies.
    Uncomment and install dependencies if you want to use it.
    """
    # try:
    #     from transformers import AutoTokenizer, AutoModelForSequenceClassification
    #     import torch
    #
    #     tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
    #     model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
    #
    #     inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    #     outputs = model(**inputs)
    #     probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
    #
    #     # FinBERT classes: negative, neutral, positive
    #     sentiment_score = probs[0][2].item() - probs[0][0].item()  # positive - negative
    #
    #     if sentiment_score > 0.2:
    #         label = 'positive'
    #     elif sentiment_score < -0.2:
    #         label = 'negative'
    #     else:
    #         label = 'neutral'
    #
    #     return {
    #         'score': sentiment_score,
    #         'label': label,
    #         'probabilities': {
    #             'negative': probs[0][0].item(),
    #             'neutral': probs[0][1].item(),
    #             'positive': probs[0][2].item()
    #         }
    #     }
    # except Exception as e:
    #     return analyze_text_sentiment(text)  # Fallback to keyword-based

    pass


if __name__ == "__main__":
    # Test sentiment analysis
    test_symbols = ['AAPL', 'TSLA', 'NVDA']

    print("=" * 60)
    print("SENTIMENT ANALYSIS TEST")
    print("=" * 60)

    for symbol in test_symbols:
        print(f"\n{symbol}:")
        print("-" * 40)

        sentiment = get_news_sentiment(symbol, lookback_days=7)

        print(f"News Count: {sentiment['news_count']}")
        print(f"Sentiment Score: {sentiment['sentiment_score']:+.3f}")
        print(f"  Positive: {sentiment['sentiment_positive']*100:.1f}%")
        print(f"  Negative: {sentiment['sentiment_negative']*100:.1f}%")
        print(f"  Neutral:  {sentiment['sentiment_neutral']*100:.1f}%")

        # Interpret
        if sentiment['sentiment_score'] > 0.3:
            print("  → Bullish sentiment")
        elif sentiment['sentiment_score'] < -0.3:
            print("  → Bearish sentiment")
        else:
            print("  → Neutral sentiment")
