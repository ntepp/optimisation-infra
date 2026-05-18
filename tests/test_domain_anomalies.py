from datetime import datetime, timezone

import pytest

from src.domain.anomalies import ThresholdEvaluator
from src.domain.metrics import MetricPoint, ServiceStatus


THRESHOLDS = {
    "cpu_usage":   {"warning": 80.0, "critical": 90.0},
    "latency_ms":  {"warning": 220.0, "critical": 320.0},
    "io_wait":     {"warning": 7.0, "critical": 11.0},
}
SERVICE_SEVERITY = {"online": None, "degraded": "WARNING", "offline": "CRITICAL"}


def _point(**overrides) -> MetricPoint:
    raw = {
        "timestamp": "2026-05-18T12:00:00Z",
        "cpu_usage": 50.0, "memory_usage": 60.0, "latency_ms": 100.0,
        "disk_usage": 40.0, "network_in_kbps": 1000.0, "network_out_kbps": 800.0,
        "io_wait": 3.0, "thread_count": 100, "active_connections": 30,
        "error_rate": 0.01, "uptime_seconds": 360000,
        "temperature_celsius": 60.0, "power_consumption_watts": 200.0,
        "service_status": {"database": "online", "api_gateway": "online", "cache": "online"},
    }
    raw.update(overrides)
    return MetricPoint.from_raw(raw)


def test_evaluator_returns_empty_for_clean_point():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    assert ev.evaluate(_point()) == []


def test_evaluator_flags_critical_when_value_above_critical_threshold():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    anomalies = ev.evaluate(_point(cpu_usage=95.0))
    assert len(anomalies) == 1
    assert anomalies[0].severity == "CRITICAL"
    assert anomalies[0].threshold == 90.0


def test_evaluator_flags_warning_for_value_between_thresholds():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    anomalies = ev.evaluate(_point(cpu_usage=85.0))
    assert len(anomalies) == 1
    assert anomalies[0].severity == "WARNING"


def test_evaluator_flags_service_degradation():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    p = _point(service_status={"database": "online", "api_gateway": "degraded", "cache": "online"})
    anomalies = ev.evaluate(p)
    assert any(a.metric == "service.api_gateway" and a.severity == "WARNING" for a in anomalies)


def test_evaluator_flags_service_offline_as_critical():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    p = _point(service_status={"database": "offline", "api_gateway": "online", "cache": "online"})
    anomalies = ev.evaluate(p)
    assert any(a.metric == "service.database" and a.severity == "CRITICAL" for a in anomalies)


def test_evaluator_handles_multiple_anomalies_in_one_point():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    p = _point(cpu_usage=95.0, latency_ms=350.0, io_wait=12.0,
               service_status={"database": "online", "api_gateway": "degraded", "cache": "online"})
    anomalies = ev.evaluate(p)
    assert len(anomalies) == 4
    severities = {a.severity for a in anomalies}
    assert "CRITICAL" in severities and "WARNING" in severities


def test_anomaly_with_explanation_returns_new_immutable_instance():
    ev = ThresholdEvaluator(THRESHOLDS, SERVICE_SEVERITY)
    original = ev.evaluate(_point(cpu_usage=95.0))[0]
    explained = original.with_explanation("test")
    assert original.explanation == ""
    assert explained.explanation == "test"
    assert original is not explained
