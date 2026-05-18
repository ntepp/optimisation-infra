from __future__ import annotations

import json

from src.adapters.outbound.sources._common import filter_window, parse_json_payload
from src.domain.metrics import MetricPoint, TimeWindow


class InlineJsonSource:
    """Reads JSON (single record or list) from a CLI string argument."""

    def __init__(self, payload: str):
        self._payload = payload

    def fetch(self, window: TimeWindow | None = None) -> list[MetricPoint]:
        raw = json.loads(self._payload)
        return filter_window(parse_json_payload(raw), window)
