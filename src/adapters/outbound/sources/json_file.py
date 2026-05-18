from __future__ import annotations

import json
from pathlib import Path

from src.adapters.outbound.sources._common import filter_window, parse_json_payload
from src.domain.metrics import MetricPoint, TimeWindow


class JsonFileSource:
    """Reads a JSON file (single record or list of records) from disk."""

    def __init__(self, path: str | Path):
        self._path = Path(path)

    def fetch(self, window: TimeWindow | None = None) -> list[MetricPoint]:
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        return filter_window(parse_json_payload(raw), window)
