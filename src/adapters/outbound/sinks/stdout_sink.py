from __future__ import annotations

import json
import sys


class StdoutSink:
    """Prints the report as pretty-printed JSON to stdout."""

    def __init__(self, stream=None):
        self._stream = stream or sys.stdout

    def emit(self, report: dict) -> None:
        self._stream.write(json.dumps(report, indent=2, ensure_ascii=False))
        self._stream.write("\n")
