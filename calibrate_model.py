"""
Model calibration tool.

Validates that predicted probabilities match actual hit rates.
Helps determine optimal confidence thresholds for signal generation.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from sklearn.calibration import calibration_curve
import os


def analyze_calibration(results_path='data/backtest_results.csv'):
    """
    Analyze model calibration from backtest results.

    Args:
        results_path: Path to backtest results CSV

    Returns:
        Dict with calibration metrics
    """
    if not os.path.exists(results_path):
        print(f"❌ Backtest results not found at {results_path}")
        print("Run backtest.py first to generate results.")
        return None

    # Load backtest results
    df = pd.read_csv(results_path)

    print("=" * 70)
    print("MODEL CALIBRATION ANALYSIS")
    print("=" * 70)
    print(f"Loaded {len(df)} backtest signals\n")

    # Check if data is corrupted (contains Series objects)
    if df['actual_return'].dtype == 'object':
        print("⚠️ WARNING: Backtest data appears corrupted!")
        print("Some values contain Series objects instead of scalars.")
        print("Run backtest.py again to regenerate clean results.\n")

        # Try to fix by extracting numeric values
        try:
            df['actual_return'] = df['actual_return'].apply(
                lambda x: float(str(x).split()[-1]) if isinstance(x, str) else x
            )
            df['hit_target'] = df['hit_target'].apply(
                lambda x: 'True' in str(x) if isinstance(x, str) else x
            )
            print("✅ Attempted to clean corrupted data\n")
        except Exception as e:
            print(f"❌ Could not fix corrupted data: {e}")
            return None

    # Convert to proper types
    df['predicted_prob'] = pd.to_numeric(df['predicted_prob'], errors='coerce')
    df['actual_return'] = pd.to_numeric(df['actual_return'], errors='coerce')
    df['hit_target'] = df['hit_target'].astype(bool)

    # Remove any remaining NaN values
    df = df.dropna(subset=['predicted_prob', 'actual_return', 'hit_target'])

    if len(df) == 0:
        print("❌ No valid data after cleaning")
        return None

    # Calculate calibration curve
    y_true = df['hit_target'].values
    y_prob = df['predicted_prob'].values

    try:
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy='quantile')
    except Exception as e:
        print(f"⚠️ Could not generate calibration curve: {e}")
        prob_true, prob_pred = None, None

    # Analyze by probability buckets
    print("-" * 70)
    print("CALIBRATION BY CONFIDENCE LEVEL")
    print("-" * 70)
    print(f"{'Predicted Range':<20} {'Count':<10} {'Hit Rate':<15} {'Calibration':<15}")
    print("-" * 70)

    bins = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    labels = ['50-60%', '60-70%', '70-80%', '80-90%', '90-100%']

    df['prob_bucket'] = pd.cut(df['predicted_prob'], bins=bins, labels=labels, include_lowest=True)

    calibration_errors = []
    for bucket in labels:
        bucket_data = df[df['prob_bucket'] == bucket]
        if len(bucket_data) == 0:
            continue

        count = len(bucket_data)
        hit_rate = bucket_data['hit_target'].mean()
        predicted_mean = bucket_data['predicted_prob'].mean()
        calibration_error = abs(hit_rate - predicted_mean)

        calibration_errors.append(calibration_error)

        # Determine if well-calibrated
        status = "✅" if calibration_error < 0.10 else "⚠️" if calibration_error < 0.20 else "❌"

        print(f"{bucket:<20} {count:<10} {hit_rate*100:>6.1f}% "
              f"(pred: {predicted_mean*100:.1f}%)  {status} Error: {calibration_error*100:.1f}%")

    # Overall metrics
    print("\n" + "-" * 70)
    print("OVERALL CALIBRATION METRICS")
    print("-" * 70)

    overall_precision = df['hit_target'].mean()
    avg_predicted_prob = df['predicted_prob'].mean()
    mean_calibration_error = np.mean(calibration_errors) if calibration_errors else 0

    print(f"Average Predicted Probability: {avg_predicted_prob*100:.1f}%")
    print(f"Actual Hit Rate (Precision):   {overall_precision*100:.1f}%")
    print(f"Overall Calibration Error:     {abs(overall_precision - avg_predicted_prob)*100:.1f}%")
    print(f"Mean Absolute Calibration Error: {mean_calibration_error*100:.1f}%")

    if mean_calibration_error < 0.10:
        print("\n✅ Model is WELL CALIBRATED (error < 10%)")
    elif mean_calibration_error < 0.20:
        print("\n⚠️ Model calibration is ACCEPTABLE but could be improved")
    else:
        print("\n❌ Model is POORLY CALIBRATED - consider retraining with calibration")

    # Recommendations
    print("\n" + "-" * 70)
    print("RECOMMENDED CONFIDENCE THRESHOLDS")
    print("-" * 70)

    # Find threshold that achieves 60% hit rate
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]:
        subset = df[df['predicted_prob'] >= threshold]
        if len(subset) == 0:
            continue
        hit_rate = subset['hit_target'].mean()
        signal_count = len(subset)

        if hit_rate >= 0.60:
            print(f"For ≥60% hit rate: Use threshold ≥{threshold:.2f} ({signal_count} signals, {hit_rate*100:.1f}% hit rate)")
            break

    # Find threshold that achieves 55% hit rate
    for threshold in [0.5, 0.55, 0.6, 0.65, 0.7]:
        subset = df[df['predicted_prob'] >= threshold]
        if len(subset) == 0:
            continue
        hit_rate = subset['hit_target'].mean()
        signal_count = len(subset)

        if hit_rate >= 0.55:
            print(f"For ≥55% hit rate: Use threshold ≥{threshold:.2f} ({signal_count} signals, {hit_rate*100:.1f}% hit rate)")
            break

    # Save calibration plot if possible
    if prob_true is not None and prob_pred is not None:
        try:
            plt.figure(figsize=(10, 6))
            plt.plot([0, 1], [0, 1], 'k--', label='Perfectly calibrated')
            plt.plot(prob_pred, prob_true, 's-', label='Model calibration')
            plt.xlabel('Predicted Probability')
            plt.ylabel('Actual Hit Rate')
            plt.title('Model Calibration Curve')
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig('data/calibration_curve.png', dpi=150, bbox_inches='tight')
            print(f"\n💾 Calibration curve saved to data/calibration_curve.png")
        except Exception as e:
            print(f"\n⚠️ Could not save calibration plot: {e}")

    print("\n" + "=" * 70)

    return {
        'overall_precision': overall_precision,
        'avg_predicted_prob': avg_predicted_prob,
        'mean_calibration_error': mean_calibration_error,
        'total_signals': len(df)
    }


if __name__ == "__main__":
    metrics = analyze_calibration()

    if metrics:
        print(f"\n✅ Calibration analysis complete!")
        print(f"Total signals analyzed: {metrics['total_signals']}")
        print(f"Mean calibration error: {metrics['mean_calibration_error']*100:.1f}%")
