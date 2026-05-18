from __future__ import annotations

from typing import Iterable

from src.domain.metrics import MetricPoint, TimeWindow


def parse_json_payload(raw: dict | list) -> list[MetricPoint]:
    """Accept a single record OR a list of records and return MetricPoints."""
    if isinstance(raw, dict):
        return [MetricPoint.from_raw(raw)]
    if isinstance(raw, list):
        return [MetricPoint.from_raw(r) for r in raw]
    raise ValueError(f"Unsupported JSON payload type: {type(raw).__name__}")


def filter_window(points: Iterable[MetricPoint], window: TimeWindow | None) -> list[MetricPoint]:
    if window is None:
        return list(points)
    return [p for p in points if window.contains(p.timestamp)]
