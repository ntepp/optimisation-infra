"""
LangGraph pipeline assembled from injected use-cases.

Each node is a thin orchestration lambda — all logic lives in the use-cases
(application/) and the domain (domain/).
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import StateGraph, START, END

from src.application.use_cases.analyze_batch import AnalyzeBatchUseCase
from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint, TimeWindow
from src.domain.recommendation import Recommendation


class PipelineState(TypedDict, total=False):
    points: list[MetricPoint]
    window: TimeWindow | None
    anomalies: list[Anomaly]
    recommendations: list[Recommendation]
    predictions: dict
    errors: list[str]


def _merge_errors(state: PipelineState, new_errors: list[str]) -> list[str]:
    return list(state.get("errors", [])) + list(new_errors)


def build_graph(uc: AnalyzeBatchUseCase):
    g = StateGraph(PipelineState)

    def ingest(state: PipelineState) -> dict:
        ingested = uc.ingest.execute(state.get("points", []))
        return {"points": ingested}

    def detect(state: PipelineState) -> dict:
        anomalies, errs = uc.detect.execute(state.get("points", []))
        return {"anomalies": anomalies, "errors": _merge_errors(state, errs)}

    def recommend(state: PipelineState) -> dict:
        recs, errs = uc.recommend.execute(state.get("anomalies", []))
        return {"recommendations": recs, "errors": _merge_errors(state, errs)}

    def predict(state: PipelineState) -> dict:
        preds, errs = uc.predict.execute(state.get("anomalies", []))
        return {"predictions": preds, "errors": _merge_errors(state, errs)}

    g.add_node("ingestion", ingest)
    g.add_node("anomaly_detection", detect)
    g.add_node("recommendation", recommend)
    g.add_node("prediction", predict)

    g.add_edge(START, "ingestion")
    g.add_edge("ingestion", "anomaly_detection")
    g.add_edge("anomaly_detection", "recommendation")
    g.add_edge("recommendation", "prediction")
    g.add_edge("prediction", END)

    return g.compile()
