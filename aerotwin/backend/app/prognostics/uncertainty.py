"""
Uncertainty Quantification
Provides uncertainty estimates for predictions and propagates uncertainty
through the prediction pipeline.
"""
import numpy as np


class UncertaintyEstimator:
    """Simple uncertainty propagation for RUL and risk predictions."""

    @staticmethod
    def prediction_interval(mean: float, std: float, confidence: float = 0.95) -> tuple[float, float]:
        """Compute prediction interval."""
        z = 1.96 if confidence >= 0.95 else 1.645 if confidence >= 0.90 else 1.28
        lower = mean - z * std
        upper = mean + z * std
        return max(0, lower), upper

    @staticmethod
    def combined_uncertainty(uncertainties: list[float]) -> float:
        """Combine independent uncertainties (root sum of squares)."""
        return float(np.sqrt(sum(u ** 2 for u in uncertainties)))

    @staticmethod
    def degradation_uncertainty(degradation: float, rate_variance: float,
                                 time_horizon: float) -> float:
        """Uncertainty in future degradation level."""
        return float(np.sqrt(rate_variance * time_horizon ** 2 + 0.01 * degradation))
