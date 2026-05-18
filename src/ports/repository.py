from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint


@runtime_checkable
class MetricRepository(Protocol):
    """Persistence for metric points."""

    def save(self, point: MetricPoint) -> None: ...
    def recent(self, n: int) -> list[MetricPoint]: ...


@runtime_checkable
class AnomalyRepository(Protocol):
    """Persistence for detected anomalies."""

    def save(self, anomaly: Anomaly) -> None: ...
    def history(self, metric: str, limit: int = 20) -> list[Anomaly]: ...
