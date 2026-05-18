"""
End-to-end smoke test of the pipeline graph with NullLLMProvider + InMemorySource.

No OpenAI key required. Validates that the wiring (container → graph → use-cases
→ ports) produces a well-formed report and that the domain logic survives the
trip through LangGraph.
"""
import json

import pytest

from src.adapters.inbound.runner import run_analysis
from src.adapters.outbound.llm.null_provider import NullLLMProvider
from src.adapters.outbound.sources.in_memory import InMemorySource
from src.domain.metrics import MetricPoint
from src.infrastructure.config import Settings


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


def _scripted_llm() -> NullLLMProvider:
    """Returns whatever the use-case asks for. The handler routes by prompt content."""
    def handler(system: str, user: str):
        # detect_anomalies prompt: "For each anomaly below, add … 'explanation' field"
        if "for each anomaly below" in user.lower():
            try:
                start = user.find("[", user.lower().find("anomalies:"))
                end = user.find("]", start) + 1
                arr = json.loads(user[start:end])
                for a in arr:
                    a["explanation"] = "auto-explanation"
                return arr
            except Exception:
                return []
        # recommend prompt: "advising a French SME CTO"
        if "advising a french" in user.lower():
            return {"recommendations": [{
                "priority": "HIGH", "action": "do_something",
                "affected_metrics": ["cpu_usage"],
                "rationale": "test recommendation",
            }]}
        # predict synthesis prompt
        if "risk_outlook" in user.lower() or "predicted_events" in user.lower():
            return {"risk_outlook": "test outlook", "predicted_events": []}
        return {}
    return NullLLMProvider(handler=handler)


def test_pipeline_runs_end_to_end_with_clean_data(tmp_path):
    settings = Settings(db_path=str(tmp_path / "test.db"), output_dir=str(tmp_path / "out"))
    points = [_point(f"2026-05-18T12:0{i}:00Z") for i in range(3)]

    report = run_analysis(
        source=InMemorySource(points),
        settings=settings,
        llm=_scripted_llm(),
    )

    assert report["records_processed"] == 3
    assert report["anomalies"] == []
    assert report["recommendations"] == []
    assert "predictions" in report
    assert report["errors"] == []


def test_pipeline_detects_anomalies_and_generates_recommendations(tmp_path):
    settings = Settings(db_path=str(tmp_path / "test.db"), output_dir=str(tmp_path / "out"))
    points = [
        _point("2026-05-18T12:00:00Z", cpu_usage=95.0, latency_ms=350.0),  # 2 anomalies
        _point("2026-05-18T12:01:00Z"),
    ]

    report = run_analysis(
        source=InMemorySource(points),
        settings=settings,
        llm=_scripted_llm(),
    )

    assert report["records_processed"] == 2
    assert len(report["anomalies"]) >= 2
    severities = {a["severity"] for a in report["anomalies"]}
    assert "CRITICAL" in severities
    assert len(report["recommendations"]) == 1
    assert report["recommendations"][0]["priority"] == "HIGH"


def test_pipeline_includes_predictions_block(tmp_path):
    settings = Settings(db_path=str(tmp_path / "test.db"), output_dir=str(tmp_path / "out"))
    points = [_point(f"2026-05-18T12:0{i}:00Z", disk_usage=float(40 + i * 5)) for i in range(5)]

    report = run_analysis(
        source=InMemorySource(points),
        settings=settings,
        llm=_scripted_llm(),
    )

    preds = report["predictions"]
    assert "next_interval" in preds
    assert "crisis_signal" in preds
    assert "service_signals" in preds
    assert "risk_outlook" in preds
    # disk_usage should have a linear forecast
    assert "disk_usage" in preds["next_interval"]
    assert preds["next_interval"]["disk_usage"]["method"] == "linear_regression"
