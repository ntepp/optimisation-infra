from datetime import datetime, timezone

import pytest

from src.adapters.outbound.persistence.in_memory_repo import (
    InMemoryAnomalyRepository, InMemoryMetricRepository,
)
from src.adapters.outbound.persistence.sqlite_repo import (
    SqliteAnomalyRepository, SqliteMetricRepository,
)
from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint


def _point(ts: str = "2026-05-18T12:00:00Z", **overrides) -> MetricPoint:
    raw = {
        "timestamp": ts,
        "cpu_usage": 50.0, "memory_usage": 60.0, "latency_ms": 100.0,
        "disk_usage": 40.0, "network_in_kbps": 1000.0, "network_out_kbps": 800.0,
        "io_wait": 3.0, "thread_count": 100, "active_connections": 30,
        "error_rate": 0.01, "uptime_seconds": 360000,
        "temperature_celsius": 60.0, "power_consumption_watts": 200.0,
        "service_status": {"database": "online", "api_gateway": "online", "cache": "online"},
    }
    raw.update(overrides)
    return MetricPoint.from_raw(raw)


# ── InMemory ────────────────────────────────────────────────────────────────

def test_in_memory_metric_repo_round_trip():
    repo = InMemoryMetricRepository()
    p = _point()
    repo.save(p)
    out = repo.recent(10)
    assert len(out) == 1
    assert out[0].cpu_usage == 50.0


def test_in_memory_metric_repo_recent_orders_by_timestamp():
    repo = InMemoryMetricRepository()
    repo.save(_point("2026-05-18T12:02:00Z", cpu_usage=2.0))
    repo.save(_point("2026-05-18T12:00:00Z", cpu_usage=0.0))
    repo.save(_point("2026-05-18T12:01:00Z", cpu_usage=1.0))
    out = repo.recent(10)
    assert [p.cpu_usage for p in out] == [0.0, 1.0, 2.0]


def test_in_memory_metric_repo_recent_zero_returns_empty():
    repo = InMemoryMetricRepository()
    repo.save(_point())
    assert repo.recent(0) == []


def test_in_memory_anomaly_repo_round_trip():
    repo = InMemoryAnomalyRepository()
    a = Anomaly(metric="cpu_usage", value=95.0, threshold=90.0,
                severity="CRITICAL", timestamp=datetime(2026, 5, 18, tzinfo=timezone.utc))
    repo.save(a)
    history = repo.history("cpu_usage")
    assert len(history) == 1
    assert history[0].metric == "cpu_usage"


def test_in_memory_anomaly_repo_filters_by_metric():
    repo = InMemoryAnomalyRepository()
    repo.save(Anomaly(metric="cpu_usage", value=95.0, threshold=90.0,
                      severity="CRITICAL", timestamp=datetime(2026, 5, 18, tzinfo=timezone.utc)))
    repo.save(Anomaly(metric="memory_usage", value=92.0, threshold=88.0,
                      severity="CRITICAL", timestamp=datetime(2026, 5, 18, tzinfo=timezone.utc)))
    assert len(repo.history("cpu_usage")) == 1
    assert len(repo.history("disk_usage")) == 0


# ── SQLite ──────────────────────────────────────────────────────────────────

def test_sqlite_metric_repo_round_trip(tmp_path):
    db = str(tmp_path / "test.db")
    repo = SqliteMetricRepository(db)
    p = _point(cpu_usage=87.0)
    repo.save(p)
    out = repo.recent(10)
    assert len(out) == 1
    assert out[0].cpu_usage == 87.0
    assert out[0].services.database == "online"


def test_sqlite_metric_repo_recent_returns_most_recent_by_timestamp(tmp_path):
    db = str(tmp_path / "test.db")
    repo = SqliteMetricRepository(db)
    repo.save(_point("2026-05-18T12:00:00Z", cpu_usage=10.0))
    repo.save(_point("2026-05-18T12:01:00Z", cpu_usage=20.0))
    repo.save(_point("2026-05-18T12:02:00Z", cpu_usage=30.0))
    out = repo.recent(2)
    assert [p.cpu_usage for p in out] == [20.0, 30.0]


def test_sqlite_anomaly_repo_round_trip(tmp_path):
    db = str(tmp_path / "test.db")
    repo = SqliteAnomalyRepository(db)
    a = Anomaly(metric="cpu_usage", value=95.0, threshold=90.0,
                severity="CRITICAL", timestamp=datetime(2026, 5, 18, 12, 0, tzinfo=timezone.utc),
                explanation="test reason")
    repo.save(a)
    out = repo.history("cpu_usage")
    assert len(out) == 1
    assert out[0].severity == "CRITICAL"
    assert out[0].explanation == "test reason"
