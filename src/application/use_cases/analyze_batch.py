from __future__ import annotations

from dataclasses import dataclass

from src.application.use_cases.detect_anomalies import DetectAnomaliesUseCase
from src.application.use_cases.ingest_metrics import IngestMetricsUseCase
from src.application.use_cases.predict import PredictUseCase
from src.application.use_cases.recommend import RecommendUseCase


@dataclass(frozen=True, slots=True)
class AnalyzeBatchUseCase:
    """Façade aggregating the four use-cases. Consumed by the LangGraph orchestrator."""

    ingest: IngestMetricsUseCase
    detect: DetectAnomaliesUseCase
    recommend: RecommendUseCase
    predict: PredictUseCase
