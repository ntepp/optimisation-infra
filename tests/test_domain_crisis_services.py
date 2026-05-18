from src.domain.crisis import CrisisDetector
from src.domain.forecasting import Forecast
from src.domain.metrics import MetricPoint, MetricSeries
from src.domain.services import ServiceSequenceAnalyzer


def _point(ts: str, **overrides) -> MetricPoint:
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


def _forecast(metric: str, pattern: str, trend: str = "increasing") -> Forecast:
    return Forecast(metric=metric, current_value=90.0, predicted_value=95.0,
                    trend=trend, pattern=pattern, method="pattern_detection")  # type: ignore[arg-type]


# ── CrisisDetector ──────────────────────────────────────────────────────────

def test_crisis_undetected_on_empty_history():
    d = CrisisDetector()
    sig = d.evaluate(MetricSeries([]), {})
    assert sig.detected is False
    assert sig.severity == "NORMAL"


def test_crisis_detected_when_all_three_metrics_above_thresholds():
    history = MetricSeries([_point("2026-05-18T12:00:00Z", cpu_usage=90.0, latency_ms=230.0, io_wait=8.0)])
    forecasts = {
        "cpu_usage": _forecast("cpu_usage", "PRECURSOR"),
        "latency_ms": _forecast("latency_ms", "RISING"),
        "io_wait": _forecast("io_wait", "STABLE"),
    }
    sig = CrisisDetector().evaluate(history, forecasts)
    assert sig.detected is True
    assert sig.severity == "CRITICAL"
    assert sig.confidence >= 0.7


def test_crisis_severity_escalates_with_rising_patterns():
    history = MetricSeries([_point("2026-05-18T12:00:00Z", cpu_usage=90.0, latency_ms=230.0, io_wait=8.0)])
    rising_forecasts = {
        m: _forecast(m, "PRECURSOR") for m in ("cpu_usage", "latency_ms", "io_wait")
    }
    sig = CrisisDetector().evaluate(history, rising_forecasts)
    assert sig.confidence == 0.9


def test_crisis_precursor_when_approaching_with_rising_patterns():
    history = MetricSeries([_point("2026-05-18T12:00:00Z", cpu_usage=75.0, latency_ms=180.0, io_wait=5.5)])
    forecasts = {
        m: _forecast(m, "PRECURSOR") for m in ("cpu_usage", "latency_ms", "io_wait")
    }
    sig = CrisisDetector().evaluate(history, forecasts)
    assert sig.detected is True
    assert sig.severity == "WARNING"


def test_crisis_undetected_when_metrics_normal():
    history = MetricSeries([_point("2026-05-18T12:00:00Z")])
    sig = CrisisDetector().evaluate(history, {})
    assert sig.detected is False


# ── ServiceSequenceAnalyzer ─────────────────────────────────────────────────

def test_service_analyzer_returns_normal_for_all_online():
    history = MetricSeries([_point(f"2026-05-18T12:0{i}:00Z") for i in range(5)])
    signals = ServiceSequenceAnalyzer().analyze(history)
    assert signals["database"].risk == "NORMAL"
    assert signals["api_gateway"].risk == "NORMAL"


def test_service_analyzer_detects_active_transition_to_degraded():
    pts = [
        _point("2026-05-18T12:00:00Z"),
        _point("2026-05-18T12:01:00Z",
               service_status={"database": "online", "api_gateway": "degraded", "cache": "online"}),
    ]
    signals = ServiceSequenceAnalyzer().analyze(MetricSeries(pts))
    assert signals["api_gateway"].active_transition is True
    assert signals["api_gateway"].risk == "WARNING"


def test_service_analyzer_critical_when_offline():
    pts = [_point("2026-05-18T12:00:00Z",
                  service_status={"database": "offline", "api_gateway": "online", "cache": "online"})]
    signals = ServiceSequenceAnalyzer().analyze(MetricSeries(pts))
    assert signals["database"].risk == "CRITICAL"
    assert signals["database"].current_status == "offline"


def test_service_analyzer_computes_issue_rate():
    pts = [
        _point("2026-05-18T12:00:00Z"),
        _point("2026-05-18T12:01:00Z",
               service_status={"database": "online", "api_gateway": "degraded", "cache": "online"}),
        _point("2026-05-18T12:02:00Z",
               service_status={"database": "online", "api_gateway": "degraded", "cache": "online"}),
        _point("2026-05-18T12:03:00Z"),
    ]
    signals = ServiceSequenceAnalyzer().analyze(MetricSeries(pts))
    assert signals["api_gateway"].issue_rate_in_history == 0.5
