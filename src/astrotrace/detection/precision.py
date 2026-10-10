"""Image-only precision profile selected on the existing 24 ESA train sequences.

CV-T04's detector and OptimizedConfig defaults are preserved. This new profile
uses existing gates only. Selection: precision with at least 95% of the frozen
development recall; test labels are used only for subsequent regression scoring.
See docs/handoffs/CV_PRECISION_REVIEW.md for the measured recall tradeoff.
"""
from .optimized import OptimizedConfig


def precision_config() -> OptimizedConfig:
    return OptimizedConfig(threshold_sigma=4.5, max_context_elongation=2.0,
                           min_score=0.3, min_aperture_snr=4.0,
                           max_peak_fraction=0.45)
