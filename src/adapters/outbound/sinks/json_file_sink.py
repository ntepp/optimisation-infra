from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class JsonFileSink:
    """Writes the report to output/report_<timestamp>.json (creates directory if missing)."""

    def __init__(self, output_dir: str | Path = "output"):
        self._output_dir = Path(output_dir)

    def emit(self, report: dict) -> str:
        self._output_dir.mkdir(parents=True, exist_ok=True)
        ts_label = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = self._output_dir / f"report_{ts_label}.json"
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)
