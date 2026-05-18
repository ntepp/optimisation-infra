from __future__ import annotations

import json

from src.domain.anomalies import Anomaly, ThresholdEvaluator
from src.domain.metrics import MetricPoint, MetricSeries
from src.ports.llm import LLMProvider
from src.ports.repository import AnomalyRepository, MetricRepository


class DetectAnomaliesUseCase:
    """Threshold-based anomaly detection + LLM-generated explanations."""

    def __init__(
        self,
        metric_repo: MetricRepository,
        anomaly_repo: AnomalyRepository,
        llm: LLMProvider,
        evaluator: ThresholdEvaluator,
        history_window: int = 10,
    ):
        self._metric_repo = metric_repo
        self._anomaly_repo = anomaly_repo
        self._llm = llm
        self._evaluator = evaluator
        self._history_window = history_window

    def execute(self, points: list[MetricPoint]) -> tuple[list[Anomaly], list[str]]:
        history = MetricSeries(self._metric_repo.recent(self._history_window))
        errors: list[str] = []
        out: list[Anomaly] = []

        for point in points:
            flagged = self._evaluator.evaluate(point)
            if not flagged:
                continue
            try:
                explained = self._explain(flagged, history)
            except Exception as exc:
                errors.append(f"[anomaly_detection] LLM explanation failed: {exc}")
                explained = flagged

            for a in explained:
                self._anomaly_repo.save(a)
            out.extend(explained)

        return out, errors

    def _explain(self, flagged: list[Anomaly], history: MetricSeries) -> list[Anomaly]:
        flagged_numeric = {a.metric for a in flagged if not a.metric.startswith("service.")}
        trend_data: dict[str, list[float]] = {}
        for metric in flagged_numeric:
            vals = history.values_of(metric)
            if vals:
                trend_data[metric] = vals[-5:]

        flagged_dicts = [a.to_dict() for a in flagged]
        prompt = (
            "For each anomaly below, add a brief (1-2 sentences) 'explanation' field "
            "describing why it is technically concerning and what it likely indicates.\n\n"
            f"Anomalies:\n{json.dumps(flagged_dicts, indent=2)}\n\n"
            f"Recent trend data (last <=5 readings):\n{json.dumps(trend_data, indent=2)}\n\n"
            "Return ONLY a JSON array of the same anomalies with the 'explanation' field added."
        )
        response = self._llm.complete_json(
            system="You are an infrastructure monitoring expert. Respond with valid JSON only.",
            user=prompt,
        )

        if not isinstance(response, list):
            return self._with_fallback_explanations(flagged)

        out: list[Anomaly] = []
        for original, explained_dict in zip(flagged, response):
            text = explained_dict.get("explanation") if isinstance(explained_dict, dict) else None
            out.append(original.with_explanation(text or self._fallback_text(original)))
        # If LLM returned more items than expected, ignore extras; fewer items, fill the rest
        for missing in flagged[len(out):]:
            out.append(missing.with_explanation(self._fallback_text(missing)))
        return out

    def _with_fallback_explanations(self, flagged: list[Anomaly]) -> list[Anomaly]:
        return [a.with_explanation(self._fallback_text(a)) for a in flagged]

    @staticmethod
    def _fallback_text(a: Anomaly) -> str:
        return f"{a.metric} = {a.value} exceeds threshold {a.threshold}."
