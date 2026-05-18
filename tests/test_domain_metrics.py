from datetime import datetime, timedelta, timezone

import pytest

from src.domain.metrics import MetricPoint, MetricSeries, ServiceStatus, TimeWindow


def _raw(ts: str = "2026-05-18T12:00:00Z", **overrides) -> dict:
    base = {
        "timestamp": ts,
        "cpu_usage": 50.0, "memory_usage": 60.0, "latency_ms": 100.0,
        "disk_usage": 40.0, "network_in_kbps": 1000.0, "network_out_kbps": 800.0,
        "io_wait": 3.0, "thread_count": 100, "active_connections": 30,
        "error_rate": 0.01, "uptime_seconds": 360000,
        "temperature_celsius": 60.0, "power_consumption_watts": 200.0,
        "service_status": {"database": "online", "api_gateway": "online", "cache": "online"},
    }
    base.update(overrides)
    return base


def test_metric_point_from_raw_parses_utc_timestamp():
    p = MetricPoint.from_raw(_raw())
    assert p.timestamp.tzinfo is not None
    assert p.timestamp.year == 2026 and p.timestamp.month == 5


def test_metric_point_from_raw_accepts_flat_service_fields():
    raw = _raw()
    del raw["service_status"]
    raw.update({
        "service_status_database": "online",
        "service_status_api_gateway": "degraded",
        "service_status_cache": "online",
    })
    p = MetricPoint.from_raw(raw)
    assert p.services.api_gateway == "degraded"


def test_metric_point_value_accessor():
    p = MetricPoint.from_raw(_raw(cpu_usage=92.0,
                                  service_status={"database": "offline", "api_gateway": "online", "cache": "online"}))
    assert p.value("cpu_usage") == 92.0
    assert p.value("service.database") == "offline"
    assert p.value("nonexistent") is None


def test_metric_point_to_flat_dict_inlines_services():
    p = MetricPoint.from_raw(_raw())
    flat = p.to_flat_dict()
    assert flat["service_status_database"] == "online"
    assert "service_status" not in flat


def test_time_window_point_contains_anchor():
    ts = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    w = TimeWindow.point(ts)
    assert w.contains(ts)
    assert not w.contains(ts + timedelta(seconds=1))


def test_time_window_from_minutes_includes_endpoints():
    anchor = datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc)
    w = TimeWindow.from_minutes(anchor, 60)
    assert w.contains(anchor)
    assert w.contains(anchor + timedelta(minutes=30))
    assert w.contains(anchor + timedelta(minutes=60))
    assert not w.contains(anchor + timedelta(minutes=61))


def test_time_window_unbounded_contains_everything():
    w = TimeWindow.unbounded()
    assert w.contains(datetime(1900, 1, 1, tzinfo=timezone.utc))
    assert w.contains(datetime(3000, 1, 1, tzinfo=timezone.utc))


def test_metric_series_values_of():
    pts = [MetricPoint.from_raw(_raw(ts=f"2026-05-18T12:0{i}:00Z", cpu_usage=float(i * 10))) for i in range(3)]
    series = MetricSeries(pts)
    assert series.values_of("cpu_usage") == [0.0, 10.0, 20.0]
    assert series.last() is pts[-1]
    assert len(series.tail(2)) == 2


def test_metric_series_empty():
    s = MetricSeries([])
    assert s.is_empty()
    assert s.last() is None
    assert s.values_of("cpu_usage") == []
