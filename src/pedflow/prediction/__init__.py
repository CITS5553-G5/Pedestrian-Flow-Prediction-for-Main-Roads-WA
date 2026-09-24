"""The shared entry point for batch prediction and future application adapters."""

from pedflow.prediction.workflow import PredictionResult, predict_sites

__all__ = ["PredictionResult", "predict_sites"]
