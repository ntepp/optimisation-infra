from __future__ import annotations

from typing import Iterable

from src.adapters.outbound.sources._common import filter_window
from src.domain.metrics import MetricPoint, TimeWindow


class InMemorySource:
    """Test source backed by an in-memory list of MetricPoint."""

    def __init__(self, points: Iterable[MetricPoint]):
        self._points = list(points)

    def fetch(self, window: TimeWindow | None = None) -> list[MetricPoint]:
        return filter_window(self._points, window)
