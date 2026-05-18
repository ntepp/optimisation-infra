from __future__ import annotations

from src.domain.metrics import MetricPoint
from src.ports.repository import MetricRepository


class IngestMetricsUseCase:
    """Persists raw metric points. The domain has already validated them."""

    def __init__(self, repo: MetricRepository):
        self._repo = repo

    def execute(self, points: list[MetricPoint]) -> list[MetricPoint]:
        for p in points:
            self._repo.save(p)
        return list(points)
