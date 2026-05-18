from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from src.domain.metrics import MetricSeries


Trend = Literal["increasing", "decreasing", "stable"]
PatternName = Literal["PRECURSOR", "RISING", "DECLINING", "STABLE", "LINEAR", "INSUFFICIENT_DATA"]


@dataclass(frozen=True, slots=True)
class Forecast:
    metric: str
    current_value: float
    predicted_value: float
    trend: Trend
    pattern: PatternName
    method: Literal["linear_regression", "pattern_detection"]


class LinearForecaster:
    """Pure linear-regression forecast over a metric series. Used for gradually drifting metrics."""

    def forecast(self, metric: str, values: list[float]) -> Forecast | None:
        if not values:
            return None
        if len(values) < 2:
            return Forecast(
                metric=metric, current_value=round(values[-1], 2),
                predicted_value=round(values[-1], 2), trend="stable",
                pattern="LINEAR", method="linear_regression",
            )
        x = np.arange(len(values), dtype=float)
        slope, intercept = np.polyfit(x, values, 1)
        predicted = float(slope * len(values) + intercept)
        trend: Trend = "increasing" if slope > 0.5 else "decreasing" if slope < -0.5 else "stable"
        return Forecast(
            metric=metric, current_value=round(values[-1], 2),
            predicted_value=round(predicted, 2), trend=trend,
            pattern="LINEAR", method="linear_regression",
        )


class PatternDetector:
    """
    Reactive-metric pattern detection (PRECURSOR / RISING / DECLINING / STABLE).

    Reactive metrics spike near-instantaneously (91% last a single 30-min interval).
    Linear regression misses these spikes; consecutive-rise patterns catch them.
    """

    def __init__(self, linear: LinearForecaster | None = None):
        self._linear = linear or LinearForecaster()

    def detect(self, metric: str, values: list[float]) -> Forecast | None:
        if not values:
            return None
        if len(values) < 2:
            return Forecast(
                metric=metric, current_value=round(values[-1], 2),
                predicted_value=round(values[-1], 2), trend="stable",
                pattern="INSUFFICIENT_DATA", method="pattern_detection",
            )

        current = values[-1]
        last3 = values[-3:] if len(values) >= 3 else []

        if len(last3) == 3 and last3[0] < last3[1] < last3[2]:
            avg_rise = (last3[2] - last3[0]) / 2
            return Forecast(
                metric=metric, current_value=round(current, 2),
                predicted_value=round(current + avg_rise, 2),
                trend="increasing", pattern="PRECURSOR", method="pattern_detection",
            )

        if values[-2] < values[-1]:
            rise = values[-1] - values[-2]
            return Forecast(
                metric=metric, current_value=round(current, 2),
                predicted_value=round(current + rise * 0.7, 2),
                trend="increasing", pattern="RISING", method="pattern_detection",
            )

        if values[-2] > values[-1]:
            drop = values[-2] - values[-1]
            return Forecast(
                metric=metric, current_value=round(current, 2),
                predicted_value=round(max(0.0, current - drop * 0.7), 2),
                trend="decreasing", pattern="DECLINING", method="pattern_detection",
            )

        fallback = self._linear.forecast(metric, values[-5:] if len(values) >= 5 else values)
        predicted = fallback.predicted_value if fallback else current
        return Forecast(
            metric=metric, current_value=round(current, 2),
            predicted_value=predicted, trend="stable",
            pattern="STABLE", method="pattern_detection",
        )


class RiskClassifier:
    """Maps a (metric, value) to NORMAL / WARNING / CRITICAL based on configured thresholds."""

    def __init__(self, thresholds: dict[str, dict[str, float]]):
        self._thresholds = thresholds

    def classify(self, metric: str, value: float) -> Literal["NORMAL", "WARNING", "CRITICAL"]:
        levels = self._thresholds.get(metric)
        if not levels:
            return "NORMAL"
        if value > levels["critical"]:
            return "CRITICAL"
        if value > levels["warning"]:
            return "WARNING"
        return "NORMAL"


def series_values(series: MetricSeries, metric: str) -> list[float]:
    return series.values_of(metric)
