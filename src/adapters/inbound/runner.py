"""
Shared inbound-adapter runner.

Both the CLI (main.py) and the Streamlit app (app.py) call `run_analysis` with
an already-built MetricSource. The runner fetches points, drives the graph,
and produces the final report dict. No I/O concerns (file paths, args, UI)
live here — those belong to the inbound adapters.
"""
from __future__ import annotations

from datetime import datetime, timezone

from src.application.dto import AnalysisReport
from src.domain.metrics import TimeWindow
from src.infrastructure.config import Settings
from src.infrastructure.container import build_pipeline
from src.ports.llm import LLMProvider
from src.ports.sources import MetricSource


def run_analysis(
    source: MetricSource,
    settings: Settings,
    window: TimeWindow | None = None,
    mode_label: str = "batch",
    llm: LLMProvider | None = None,
) -> dict:
    """Fetch metrics from a source, run the pipeline, return the report dict."""
    graph = build_pipeline(settings, llm=llm)
    points = list(source.fetch(window))

    initial_state = {
        "points": points,
        "window": window,
        "anomalies": [],
        "recommendations": [],
        "predictions": {},
        "errors": [],
    }
    result = graph.invoke(initial_state)

    report = AnalysisReport(
        generated_at=datetime.now(timezone.utc),
        records_processed=len(result.get("points", [])),
        anomalies=result.get("anomalies", []),
        recommendations=result.get("recommendations", []),
        predictions=result.get("predictions", {}),
        errors=result.get("errors", []),
        mode=mode_label,
    )
    return report.to_dict()
