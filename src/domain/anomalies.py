from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from src.domain.metrics import MetricPoint


Severity = Literal["WARNING", "CRITICAL"]


@dataclass(frozen=True, slots=True)
class Threshold:
    metric: str
    warning: float
    critical: float


@dataclass(frozen=True, slots=True)
class Anomaly:
    metric: str
    value: float | str
    threshold: float | str
    severity: Severity
    timestamp: datetime
    explanation: str = ""

    def with_explanation(self, text: str) -> "Anomaly":
        return Anomaly(
            metric=self.metric,
            value=self.value,
            threshold=self.threshold,
            severity=self.severity,
            timestamp=self.timestamp,
            explanation=text,
        )

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "value": self.value,
            "threshold": self.threshold,
            "severity": self.severity,
            "explanation": self.explanation,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
        }


class ThresholdEvaluator:
    """Pure rule-based anomaly detection. No I/O, no LLM."""

    def __init__(
        self,
        thresholds: dict[str, dict[str, float]],
        service_status_severity: dict[str, str | None],
    ):
        self._thresholds = {
            name: Threshold(metric=name, warning=lvl["warning"], critical=lvl["critical"])
            for name, lvl in thresholds.items()
        }
        self._service_severity = service_status_severity

    def evaluate(self, point: MetricPoint) -> list[Anomaly]:
        flagged: list[Anomaly] = []

        for metric, threshold in self._thresholds.items():
            value = point.value(metric)
            if not isinstance(value, (int, float)):
                continue
            if value > threshold.critical:
                flagged.append(Anomaly(
                    metric=metric, value=float(value), threshold=threshold.critical,
                    severity="CRITICAL", timestamp=point.timestamp,
                ))
            elif value > threshold.warning:
                flagged.append(Anomaly(
                    metric=metric, value=float(value), threshold=threshold.warning,
                    severity="WARNING", timestamp=point.timestamp,
                ))

        for svc in ("database", "api_gateway", "cache"):
            status = point.value(f"service.{svc}")
            if not isinstance(status, str):
                continue
            severity = self._service_severity.get(status)
            if severity in ("WARNING", "CRITICAL"):
                flagged.append(Anomaly(
                    metric=f"service.{svc}", value=status, threshold="online",
                    severity=severity,  # type: ignore[arg-type]
                    timestamp=point.timestamp,
                ))

        return flagged
