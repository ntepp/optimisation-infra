from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReportSink(Protocol):
    """Outbound sink for the final analysis report. Returns a URI/path or None."""

    def emit(self, report: dict) -> str | None: ...
