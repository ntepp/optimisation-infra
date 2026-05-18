from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.domain.forecasting import Forecast
from src.domain.metrics import MetricSeries


Severity = Literal["NORMAL", "WARNING", "CRITICAL"]


@dataclass(frozen=True, slots=True)
class CrisisSignature:
    detected: bool
    severity: Severity
    confidence: float
    description: str

    def to_dict(self) -> dict:
        return {
            "detected": self.detected,
            "severity": self.severity,
            "confidence": self.confidence,
            "description": self.description,
        }


class CrisisDetector:
    """
    Multi-metric crisis signature detector.

    Data analysis insight: every API Gateway degradation co-occurs with
    cpu > 85%, latency > 220ms and io_wait > 7% simultaneously. Single-metric
    regression misses these synchronized spikes.
    """

    CRISIS_METRICS = ("cpu_usage", "latency_ms", "io_wait")
    CRISIS_THRESHOLDS = {"cpu_usage": 85.0, "latency_ms": 220.0, "io_wait": 7.0}
    APPROACH_THRESHOLDS = {"cpu_usage": 70.0, "latency_ms": 170.0, "io_wait": 5.0}

    def evaluate(self, history: MetricSeries, forecasts: dict[str, Forecast]) -> CrisisSignature:
        last = history.last()
        if last is None:
            return CrisisSignature(False, "NORMAL", 0.0, "")

        cpu = float(last.value("cpu_usage") or 0)
        lat = float(last.value("latency_ms") or 0)
        io  = float(last.value("io_wait") or 0)

        rising = sum(
            1 for m in self.CRISIS_METRICS
            if (f := forecasts.get(m)) is not None and f.pattern in ("PRECURSOR", "RISING")
        )

        in_crisis = (
            cpu > self.CRISIS_THRESHOLDS["cpu_usage"]
            and lat > self.CRISIS_THRESHOLDS["latency_ms"]
            and io  > self.CRISIS_THRESHOLDS["io_wait"]
        )
        approaching = (
            cpu > self.APPROACH_THRESHOLDS["cpu_usage"]
            and lat > self.APPROACH_THRESHOLDS["latency_ms"]
            and io  > self.APPROACH_THRESHOLDS["io_wait"]
        )

        if in_crisis and rising >= 2:
            return CrisisSignature(True, "CRITICAL", 0.9,
                "Crisis signature active and escalating — CPU, latency and IO all rising")
        if in_crisis:
            return CrisisSignature(True, "CRITICAL", 0.7,
                "Crisis signature active (CPU + latency + IO all above thresholds)")
        if approaching and rising >= 2:
            return CrisisSignature(True, "WARNING", 0.6,
                "Crisis precursor — CPU, latency and IO converging upward")
        return CrisisSignature(False, "NORMAL", 0.0, "")
