import pandas as pd
import numpy as np


# =====================================================
# RISK ADJUSTMENT & CONFIDENCE CALIBRATION
# =====================================================

def adjust_confidence_for_risk_factors(base_confidence, stock_data):
    """
    Reduce confidence when high-risk factors are present.

    Args:
        base_confidence: Raw model probability (0-1)
        stock_data: Dict or Series with risk indicators

    Returns:
        adjusted_confidence: Risk-adjusted probability
        risk_factors: List of identified risk factors
    """
    adjusted_confidence = base_confidence
    risk_factors = []

    # Technical breakdown penalty
    if stock_data.get('pct_from_high', 0) < -20:  # Down >20% from 52-week high
        adjusted_confidence *= 0.85
        risk_factors.append("TECHNICAL_BREAKDOWN")

    # Severe drawdown penalty
    if stock_data.get('pct_from_high', 0) < -30:
        adjusted_confidence *= 0.75
        risk_factors.append("SEVERE_DRAWDOWN")

    # Volume declining on weakness
    if stock_data.get('volume_trend', 0) < -0.2:  # Volume down 20%+
        adjusted_confidence *= 0.90
        risk_factors.append("WEAK_VOLUME")

    # High volatility penalty
    if stock_data.get('volatility_ratio', 1.0) > 2.0:  # 2x normal volatility
        adjusted_confidence *= 0.85
        risk_factors.append("HIGH_VOLATILITY")

    # Bearish pattern (below MA50 and MA200)
    if stock_data.get('below_ma50', False) and stock_data.get('below_ma200', False):
        adjusted_confidence *= 0.80
        risk_factors.append("DEATH_CROSS_ZONE")

    # Extended rally penalty (chase risk)
    if stock_data.get('pct_from_low', 0) > 100:  # Up >100% from 52-week low
        adjusted_confidence *= 0.90
        risk_factors.append("EXTENDED_RALLY")

    return adjusted_confidence, risk_factors


def check_failure_patterns(stock_data, base_confidence):
    """
    Identify known failure patterns and reduce confidence.

    Returns:
        adjusted_confidence: Confidence after pattern checks
        failure_patterns: List of identified failure patterns
    """
    adjusted_confidence = base_confidence
    failure_patterns = []

    # Pattern 1: Parabolic rise then sharp drop
    recent_gain = stock_data.get('pct_from_low', 0)
    recent_drop = stock_data.get('recent_1w_return', 0)

    if recent_gain > 200 and recent_drop < -20:
        adjusted_confidence *= 0.60
        failure_patterns.append("PARABOLIC_REVERSAL")

    # Pattern 2: Failed breakout (near highs but falling)
    pct_from_high = stock_data.get('pct_from_high', 0)
    if -15 < pct_from_high < -5 and recent_drop < -10:
        adjusted_confidence *= 0.75
        failure_patterns.append("FAILED_BREAKOUT")

    # Pattern 3: Distribution pattern (selling into strength)
    if stock_data.get('volume_trend', 0) < 0 and stock_data.get('price_trend', 0) < 0:
        adjusted_confidence *= 0.80
        failure_patterns.append("DISTRIBUTION_PATTERN")

    # Pattern 4: Extreme overbought with reversal
    if stock_data.get('rsi', 50) > 80 and recent_drop < -5:
        adjusted_confidence *= 0.70
        failure_patterns.append("OVERBOUGHT_REVERSAL")

    return adjusted_confidence, failure_patterns


def calculate_setup_quality_score(stock_data):
    """
    Rate the quality of the trading setup independently of model confidence.

    Returns:
        score: Quality score 0-100
        quality_factors: Dict of contributing factors
    """
    score = 50  # Start neutral
    quality_factors = {}

    # POSITIVE FACTORS

    # Volume confirmation (increasing on rally)
    if stock_data.get('volume_trend', 0) > 0.1:
        score += 10
        quality_factors['volume_confirmation'] = True

    # Strong relative strength vs market
    if stock_data.get('relative_strength', 0) > 0.1:
        score += 10
        quality_factors['relative_strength'] = True

    # Bullish moving average alignment (MA10 > MA20 > MA50)
    if stock_data.get('ma_alignment_bullish', False):
        score += 15
        quality_factors['ma_alignment'] = True

    # Consolidation after rally (healthy pullback)
    pct_from_high = stock_data.get('pct_from_high', 0)
    if -10 < pct_from_high < -2:
        score += 10
        quality_factors['healthy_pullback'] = True

    # Lower volatility (more stable)
    if stock_data.get('volatility_ratio', 1.5) < 1.2:
        score += 5
        quality_factors['low_volatility'] = True

    # NEGATIVE FACTORS

    # Technical breakdown
    if stock_data.get('below_ma50', False) and stock_data.get('below_ma200', False):
        score -= 20
        quality_factors['technical_breakdown'] = True

    # Weak volume
    if stock_data.get('volume_trend', 0) < -0.2:
        score -= 15
        quality_factors['weak_volume'] = True

    # Extended move
    if stock_data.get('pct_from_low', 0) > 150:
        score -= 10
        quality_factors['overextended'] = True

    # High volatility
    if stock_data.get('volatility_ratio', 1.0) > 2.0:
        score -= 10
        quality_factors['high_volatility'] = True

    return min(100, max(0, score)), quality_factors


def categorize_confidence(model_confidence, setup_quality_score):
    """
    Convert confidence scores into actionable trading categories.

    Args:
        model_confidence: Risk-adjusted model confidence (0-1)
        setup_quality_score: Setup quality score (0-100)

    Returns:
        category: Confidence category string
        position_size: Recommended position size (0-1)
        action: Trading action recommendation
    """
    # Combine model confidence (70% weight) with setup quality (30% weight)
    normalized_quality = setup_quality_score / 100.0
    final_score = (model_confidence * 0.7) + (normalized_quality * 0.3)

    if final_score >= 0.80:
        return "HIGH_CONFIDENCE", 1.0, "Full position - Strong setup"
    elif final_score >= 0.70:
        return "GOOD_CONFIDENCE", 0.75, "75% position - Good setup"
    elif final_score >= 0.60:
        return "MODERATE_CONFIDENCE", 0.50, "50% position - Acceptable setup"
    elif final_score >= 0.50:
        return "LOW_CONFIDENCE", 0.25, "25% position - Marginal setup"
    else:
        return "NO_CONFIDENCE", 0.0, "Skip - Poor setup"


def get_final_signal_assessment(base_prob, stock_data):
    """
    Complete signal assessment pipeline.

    Args:
        base_prob: Raw model probability
        stock_data: Dict with stock indicators

    Returns:
        assessment: Dict with full assessment details
    """
    # Step 1: Risk adjustments
    adj_conf, risk_factors = adjust_confidence_for_risk_factors(base_prob, stock_data)

    # Step 2: Check for failure patterns
    adj_conf, failure_patterns = check_failure_patterns(stock_data, adj_conf)

    # Step 3: Calculate setup quality
    setup_quality, quality_factors = calculate_setup_quality_score(stock_data)

    # Step 4: Categorize final confidence
    category, position_size, action = categorize_confidence(adj_conf, setup_quality)

    return {
        'base_probability': base_prob,
        'adjusted_probability': adj_conf,
        'adjustment_factor': adj_conf / base_prob if base_prob > 0 else 0,
        'setup_quality_score': setup_quality,
        'final_score': (adj_conf * 0.7) + (setup_quality / 100.0 * 0.3),
        'confidence_category': category,
        'position_size': position_size,
        'action': action,
        'risk_factors': risk_factors,
        'failure_patterns': failure_patterns,
        'quality_factors': quality_factors
    }


if __name__ == "__main__":
    # Example usage
    example_stock = {
        'pct_from_high': -25,  # Down 25% from 52-week high
        'pct_from_low': 80,    # Up 80% from 52-week low
        'volume_trend': -0.15,  # Volume declining
        'volatility_ratio': 1.8,
        'below_ma50': True,
        'below_ma200': False,
        'recent_1w_return': -8,
        'relative_strength': -0.05,
        'ma_alignment_bullish': False
    }

    base_probability = 0.95  # 95% confidence from model

    assessment = get_final_signal_assessment(base_probability, example_stock)

    print(f"Base Probability: {assessment['base_probability']:.1%}")
    print(f"Adjusted Probability: {assessment['adjusted_probability']:.1%}")
    print(f"Setup Quality: {assessment['setup_quality_score']}/100")
    print(f"Final Score: {assessment['final_score']:.1%}")
    print(f"Category: {assessment['confidence_category']}")
    print(f"Action: {assessment['action']}")
    print(f"Position Size: {assessment['position_size']:.0%}")
    print(f"\nRisk Factors: {assessment['risk_factors']}")
    print(f"Failure Patterns: {assessment['failure_patterns']}")
