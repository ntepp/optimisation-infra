from __future__ import annotations

from dataclasses import dataclass, field, fields
from datetime import datetime, timedelta, timezone
from typing import Iterable


def _parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


@dataclass(frozen=True, slots=True)
class ServiceStatus:
    database: str
    api_gateway: str
    cache: str

    def as_dict(self) -> dict[str, str]:
        return {"database": self.database, "api_gateway": self.api_gateway, "cache": self.cache}


@dataclass(frozen=True, slots=True)
class MetricPoint:
    timestamp: datetime
    cpu_usage: float
    memory_usage: float
    latency_ms: float
    disk_usage: float
    network_in_kbps: float
    network_out_kbps: float
    io_wait: float
    thread_count: int
    active_connections: int
    error_rate: float
    uptime_seconds: int
    temperature_celsius: float
    power_consumption_watts: float
    services: ServiceStatus

    @classmethod
    def from_raw(cls, raw: dict) -> "MetricPoint":
        ts = raw["timestamp"]
        dt = _parse_utc(ts) if isinstance(ts, str) else ts
        svc = raw.get("service_status") or {
            "database": raw.get("service_status_database", "online"),
            "api_gateway": raw.get("service_status_api_gateway", "online"),
            "cache": raw.get("service_status_cache", "online"),
        }
        return cls(
            timestamp=dt,
            cpu_usage=float(raw["cpu_usage"]),
            memory_usage=float(raw["memory_usage"]),
            latency_ms=float(raw["latency_ms"]),
            disk_usage=float(raw["disk_usage"]),
            network_in_kbps=float(raw["network_in_kbps"]),
            network_out_kbps=float(raw["network_out_kbps"]),
            io_wait=float(raw["io_wait"]),
            thread_count=int(raw["thread_count"]),
            active_connections=int(raw["active_connections"]),
            error_rate=float(raw["error_rate"]),
            uptime_seconds=int(raw["uptime_seconds"]),
            temperature_celsius=float(raw["temperature_celsius"]),
            power_consumption_watts=float(raw["power_consumption_watts"]),
            services=ServiceStatus(
                database=svc.get("database", "online"),
                api_gateway=svc.get("api_gateway", "online"),
                cache=svc.get("cache", "online"),
            ),
        )

    def value(self, name: str) -> float | int | str | None:
        if name == "service.database":     return self.services.database
        if name == "service.api_gateway":  return self.services.api_gateway
        if name == "service.cache":        return self.services.cache
        return getattr(self, name, None)

    def to_flat_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "latency_ms": self.latency_ms,
            "disk_usage": self.disk_usage,
            "network_in_kbps": self.network_in_kbps,
            "network_out_kbps": self.network_out_kbps,
            "io_wait": self.io_wait,
            "thread_count": self.thread_count,
            "active_connections": self.active_connections,
            "error_rate": self.error_rate,
            "uptime_seconds": self.uptime_seconds,
            "temperature_celsius": self.temperature_celsius,
            "power_consumption_watts": self.power_consumption_watts,
            "service_status_database": self.services.database,
            "service_status_api_gateway": self.services.api_gateway,
            "service_status_cache": self.services.cache,
        }


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: datetime | None
    end: datetime | None

    @classmethod
    def point(cls, ts: datetime) -> "TimeWindow":
        return cls(start=ts, end=ts)

    @classmethod
    def from_minutes(cls, anchor: datetime, minutes: int) -> "TimeWindow":
        return cls(start=anchor, end=anchor + timedelta(minutes=minutes))

    @classmethod
    def unbounded(cls) -> "TimeWindow":
        return cls(start=None, end=None)

    def contains(self, ts: datetime) -> bool:
        if self.start is not None and ts < self.start:
            return False
        if self.end is not None and ts > self.end:
            return False
        return True


NUMERIC_FIELDS = (
    "cpu_usage", "memory_usage", "latency_ms", "disk_usage",
    "network_in_kbps", "network_out_kbps", "io_wait",
    "thread_count", "active_connections", "error_rate", "uptime_seconds",
    "temperature_celsius", "power_consumption_watts",
)


class MetricSeries:
    """Sequence wrapper around list[MetricPoint] providing analytical helpers."""

    __slots__ = ("_points",)

    def __init__(self, points: Iterable[MetricPoint]):
        self._points = list(points)

    def __len__(self) -> int:
        return len(self._points)

    def __iter__(self):
        return iter(self._points)

    def __getitem__(self, idx):
        return self._points[idx]

    @property
    def points(self) -> list[MetricPoint]:
        return list(self._points)

    def is_empty(self) -> bool:
        return not self._points

    def last(self) -> MetricPoint | None:
        return self._points[-1] if self._points else None

    def tail(self, n: int) -> "MetricSeries":
        return MetricSeries(self._points[-n:] if n > 0 else [])

    def values_of(self, metric: str) -> list[float]:
        vals: list[float] = []
        for p in self._points:
            v = p.value(metric)
            if isinstance(v, (int, float)):
                vals.append(float(v))
        return vals

    def statuses_of(self, service: str) -> list[str]:
        attr = service
        return [p.value(f"service.{attr}") for p in self._points]  # type: ignore[misc]
