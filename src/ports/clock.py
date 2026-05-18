from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Time source. Injected for testability."""

    def now_utc(self) -> datetime: ...


class SystemClock:
    """Default Clock implementation backed by the system clock."""

    def now_utc(self) -> datetime:
        return datetime.now(timezone.utc)
