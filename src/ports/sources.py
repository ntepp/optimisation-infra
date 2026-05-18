from __future__ import annotations

from typing import Iterable, Protocol, runtime_checkable

from src.domain.metrics import MetricPoint, TimeWindow


@runtime_checkable
class MetricSource(Protocol):
    """Inbound data source for metric points. Implementations: file, stdin, inline, HTTP, …"""

    def fetch(self, window: TimeWindow | None = None) -> Iterable[MetricPoint]: ...
