from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint, ServiceStatus, _parse_utc


def _connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(db_path: str) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True) if Path(db_path).parent.as_posix() not in ("", ".") else None
    with _connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id                          INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp                   TEXT NOT NULL,
                cpu_usage                   REAL,
                memory_usage                REAL,
                latency_ms                  REAL,
                disk_usage                  REAL,
                network_in_kbps             REAL,
                network_out_kbps            REAL,
                io_wait                     REAL,
                thread_count                INTEGER,
                active_connections          INTEGER,
                error_rate                  REAL,
                uptime_seconds              INTEGER,
                temperature_celsius         REAL,
                power_consumption_watts     REAL,
                service_status_database     TEXT,
                service_status_api_gateway  TEXT,
                service_status_cache        TEXT,
                processed_at                TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS anomalies (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_timestamp TEXT NOT NULL,
                metric_name      TEXT NOT NULL,
                value            TEXT NOT NULL,
                threshold        TEXT,
                severity         TEXT NOT NULL,
                explanation      TEXT,
                detected_at      TEXT NOT NULL
            )
        """)


def _row_to_point(row: sqlite3.Row) -> MetricPoint:
    ts = _parse_utc(row["timestamp"]) if isinstance(row["timestamp"], str) else row["timestamp"]
    return MetricPoint(
        timestamp=ts,
        cpu_usage=row["cpu_usage"] or 0.0,
        memory_usage=row["memory_usage"] or 0.0,
        latency_ms=row["latency_ms"] or 0.0,
        disk_usage=row["disk_usage"] or 0.0,
        network_in_kbps=row["network_in_kbps"] or 0.0,
        network_out_kbps=row["network_out_kbps"] or 0.0,
        io_wait=row["io_wait"] or 0.0,
        thread_count=row["thread_count"] or 0,
        active_connections=row["active_connections"] or 0,
        error_rate=row["error_rate"] or 0.0,
        uptime_seconds=row["uptime_seconds"] or 0,
        temperature_celsius=row["temperature_celsius"] or 0.0,
        power_consumption_watts=row["power_consumption_watts"] or 0.0,
        services=ServiceStatus(
            database=row["service_status_database"] or "online",
            api_gateway=row["service_status_api_gateway"] or "online",
            cache=row["service_status_cache"] or "online",
        ),
    )


class SqliteMetricRepository:
    """SQLite-backed implementation of MetricRepository."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        init_schema(db_path)

    def save(self, point: MetricPoint) -> None:
        with _connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO metrics (
                    timestamp, cpu_usage, memory_usage, latency_ms, disk_usage,
                    network_in_kbps, network_out_kbps, io_wait, thread_count,
                    active_connections, error_rate, uptime_seconds,
                    temperature_celsius, power_consumption_watts,
                    service_status_database, service_status_api_gateway,
                    service_status_cache, processed_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    point.timestamp.isoformat(),
                    point.cpu_usage, point.memory_usage, point.latency_ms,
                    point.disk_usage, point.network_in_kbps, point.network_out_kbps,
                    point.io_wait, point.thread_count, point.active_connections,
                    point.error_rate, point.uptime_seconds,
                    point.temperature_celsius, point.power_consumption_watts,
                    point.services.database,
                    point.services.api_gateway,
                    point.services.cache,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def recent(self, n: int) -> list[MetricPoint]:
        with _connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM metrics ORDER BY timestamp DESC LIMIT ?", (n,)
            ).fetchall()
        return [_row_to_point(r) for r in reversed(rows)]


class SqliteAnomalyRepository:
    """SQLite-backed implementation of AnomalyRepository."""

    def __init__(self, db_path: str):
        self._db_path = db_path
        init_schema(db_path)

    def save(self, anomaly: Anomaly) -> None:
        with _connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO anomalies (
                    metric_timestamp, metric_name, value, threshold,
                    severity, explanation, detected_at
                ) VALUES (?,?,?,?,?,?,?)
                """,
                (
                    anomaly.timestamp.isoformat() if isinstance(anomaly.timestamp, datetime) else str(anomaly.timestamp),
                    anomaly.metric,
                    str(anomaly.value),
                    str(anomaly.threshold),
                    anomaly.severity,
                    anomaly.explanation,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def history(self, metric: str, limit: int = 20) -> list[Anomaly]:
        with _connect(self._db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM anomalies WHERE metric_name = ? ORDER BY detected_at DESC LIMIT ?",
                (metric, limit),
            ).fetchall()
        out: list[Anomaly] = []
        for r in rows:
            ts = r["metric_timestamp"]
            try:
                dt = _parse_utc(ts) if isinstance(ts, str) and ts else datetime.now(timezone.utc)
            except ValueError:
                dt = datetime.now(timezone.utc)
            out.append(Anomaly(
                metric=r["metric_name"],
                value=r["value"],
                threshold=r["threshold"] or "",
                severity=r["severity"],  # type: ignore[arg-type]
                timestamp=dt,
                explanation=r["explanation"] or "",
            ))
        return out
