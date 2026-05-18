"""
Composition root: wires ports to adapters, builds use-cases, returns a compiled graph.

Inbound adapters (CLI, Streamlit) call `build_*` functions here. The container
is the only place where concrete adapter classes are referenced — domain and
application layers know only the ports.
"""
from __future__ import annotations

from src.adapters.outbound.llm.null_provider import NullLLMProvider
from src.adapters.outbound.llm.openai_provider import OpenAIProvider
from src.adapters.outbound.persistence.sqlite_repo import (
    SqliteAnomalyRepository, SqliteMetricRepository,
)
from src.adapters.outbound.sources.inline_json import InlineJsonSource
from src.adapters.outbound.sources.json_file import JsonFileSource
from src.adapters.outbound.sources.stdin_json import StdinJsonSource
from src.application.use_cases.analyze_batch import AnalyzeBatchUseCase
from src.application.use_cases.detect_anomalies import DetectAnomaliesUseCase
from src.application.use_cases.ingest_metrics import IngestMetricsUseCase
from src.application.use_cases.predict import PredictUseCase
from src.application.use_cases.recommend import RecommendUseCase
from src.domain.anomalies import ThresholdEvaluator
from src.domain.forecasting import LinearForecaster, PatternDetector, RiskClassifier
from src.infrastructure.config import Settings
from src.infrastructure.pipeline_graph import build_graph
from src.ports.llm import LLMProvider
from src.ports.sources import MetricSource


def build_llm(settings: Settings) -> LLMProvider:
    """Construct the LLM provider. NullLLMProvider is used when no API key is configured."""
    if not settings.openai_api_key:
        return NullLLMProvider(payload={})
    return OpenAIProvider(model=settings.model_name, api_key=settings.openai_api_key)


def build_analyze_use_case(settings: Settings, llm: LLMProvider | None = None) -> AnalyzeBatchUseCase:
    metric_repo = SqliteMetricRepository(settings.db_path)
    anomaly_repo = SqliteAnomalyRepository(settings.db_path)
    llm_provider = llm or build_llm(settings)

    evaluator = ThresholdEvaluator(settings.thresholds, settings.service_status_severity)
    risk_classifier = RiskClassifier(settings.thresholds)
    linear = LinearForecaster()
    pattern = PatternDetector(linear)

    return AnalyzeBatchUseCase(
        ingest=IngestMetricsUseCase(metric_repo),
        detect=DetectAnomaliesUseCase(
            metric_repo=metric_repo,
            anomaly_repo=anomaly_repo,
            llm=llm_provider,
            evaluator=evaluator,
            history_window=settings.history_anomaly,
        ),
        recommend=RecommendUseCase(
            repo=metric_repo, llm=llm_provider,
            history_window=settings.history_recommendation,
        ),
        predict=PredictUseCase(
            repo=metric_repo, llm=llm_provider,
            risk_classifier=risk_classifier,
            linear=linear, pattern=pattern,
            history_window=settings.history_prediction,
        ),
    )


def build_pipeline(settings: Settings, llm: LLMProvider | None = None):
    """Returns the compiled LangGraph ready to `.invoke(state)`."""
    uc = build_analyze_use_case(settings, llm=llm)
    return build_graph(uc)


def build_source(source_type: str, *, input_path: str | None = None, inline_json: str | None = None) -> MetricSource:
    if source_type == "file":
        if not input_path:
            raise ValueError("--input is required when --source=file")
        return JsonFileSource(input_path)
    if source_type == "stdin":
        return StdinJsonSource()
    if source_type == "inline":
        if not inline_json:
            raise ValueError("--json is required when --source=inline")
        return InlineJsonSource(inline_json)
    raise ValueError(f"unknown source type: {source_type}")
