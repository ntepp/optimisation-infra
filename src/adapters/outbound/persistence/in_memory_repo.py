from __future__ import annotations

from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint


class InMemoryMetricRepository:
    """In-memory MetricRepository for tests. Preserves insertion order."""

    def __init__(self) -> None:
        self._points: list[MetricPoint] = []

    def save(self, point: MetricPoint) -> None:
        self._points.append(point)

    def recent(self, n: int) -> list[MetricPoint]:
        if n <= 0:
            return []
        ordered = sorted(self._points, key=lambda p: p.timestamp)
        return ordered[-n:]


class InMemoryAnomalyRepository:
    """In-memory AnomalyRepository for tests."""

    def __init__(self) -> None:
        self._anomalies: list[Anomaly] = []

    def save(self, anomaly: Anomaly) -> None:
        self._anomalies.append(anomaly)

    def history(self, metric: str, limit: int = 20) -> list[Anomaly]:
        matching = [a for a in self._anomalies if a.metric == metric]
        return matching[-limit:][::-1] if limit > 0 else []
