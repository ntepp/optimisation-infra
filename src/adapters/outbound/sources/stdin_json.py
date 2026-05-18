from __future__ import annotations

import json
import sys

from src.adapters.outbound.sources._common import filter_window, parse_json_payload
from src.domain.metrics import MetricPoint, TimeWindow


class StdinJsonSource:
    """Reads JSON (single record or list) from stdin, blocking until EOF."""

    def __init__(self, stream=None):
        self._stream = stream or sys.stdin

    def fetch(self, window: TimeWindow | None = None) -> list[MetricPoint]:
        raw = json.loads(self._stream.read())
        return filter_window(parse_json_payload(raw), window)
