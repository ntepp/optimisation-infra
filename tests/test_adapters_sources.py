import io
import json
from datetime import datetime, timezone

import pytest

from src.adapters.outbound.sources.inline_json import InlineJsonSource
from src.adapters.outbound.sources.json_file import JsonFileSource
from src.adapters.outbound.sources.stdin_json import StdinJsonSource
from src.domain.metrics import TimeWindow


def _record(ts: str = "2026-05-18T12:00:00Z", cpu: float = 50.0) -> dict:
    return {
        "timestamp": ts,
        "cpu_usage": cpu, "memory_usage": 60.0, "latency_ms": 100.0,
        "disk_usage": 40.0, "network_in_kbps": 1000.0, "network_out_kbps": 800.0,
        "io_wait": 3.0, "thread_count": 100, "active_connections": 30,
        "error_rate": 0.01, "uptime_seconds": 360000,
        "temperature_celsius": 60.0, "power_consumption_watts": 200.0,
        "service_status": {"database": "online", "api_gateway": "online", "cache": "online"},
    }


# ── JsonFileSource ──────────────────────────────────────────────────────────

def test_json_file_source_reads_list(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps([_record(), _record(ts="2026-05-18T12:01:00Z", cpu=60.0)]))
    points = list(JsonFileSource(path).fetch())
    assert len(points) == 2
    assert points[1].cpu_usage == 60.0


def test_json_file_source_reads_single_object(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps(_record()))
    points = list(JsonFileSource(path).fetch())
    assert len(points) == 1


def test_json_file_source_applies_window(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps([
        _record(ts="2026-05-18T12:00:00Z"),
        _record(ts="2026-05-18T13:00:00Z"),
        _record(ts="2026-05-18T14:00:00Z"),
    ]))
    anchor = datetime(2026, 5, 18, 12, 30, tzinfo=timezone.utc)
    end = datetime(2026, 5, 18, 13, 30, tzinfo=timezone.utc)
    points = list(JsonFileSource(path).fetch(TimeWindow(start=anchor, end=end)))
    assert len(points) == 1
    assert points[0].timestamp.hour == 13


# ── StdinJsonSource ─────────────────────────────────────────────────────────

def test_stdin_json_source_reads_piped_list():
    stream = io.StringIO(json.dumps([_record(), _record(ts="2026-05-18T12:01:00Z")]))
    points = list(StdinJsonSource(stream=stream).fetch())
    assert len(points) == 2


def test_stdin_json_source_reads_single_record():
    stream = io.StringIO(json.dumps(_record(cpu=92.0)))
    points = list(StdinJsonSource(stream=stream).fetch())
    assert len(points) == 1
    assert points[0].cpu_usage == 92.0


# ── InlineJsonSource ────────────────────────────────────────────────────────

def test_inline_json_source_reads_single_record():
    payload = json.dumps(_record(cpu=88.0))
    points = list(InlineJsonSource(payload).fetch())
    assert len(points) == 1
    assert points[0].cpu_usage == 88.0


def test_inline_json_source_reads_list():
    payload = json.dumps([_record(), _record(ts="2026-05-18T12:01:00Z")])
    points = list(InlineJsonSource(payload).fetch())
    assert len(points) == 2


def test_inline_json_source_invalid_json_raises():
    with pytest.raises(Exception):
        list(InlineJsonSource("not json").fetch())
