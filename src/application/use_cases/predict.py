from __future__ import annotations

import json

from src.domain.anomalies import Anomaly
from src.domain.crisis import CrisisDetector
from src.domain.forecasting import (
    Forecast, LinearForecaster, PatternDetector, RiskClassifier,
)
from src.domain.metrics import MetricSeries
from src.domain.services import ServiceSequenceAnalyzer
from src.ports.llm import LLMProvider
from src.ports.repository import MetricRepository


GRADUAL_METRICS = ("disk_usage", "memory_usage", "power_consumption_watts")
REACTIVE_METRICS = ("cpu_usage", "latency_ms", "io_wait", "error_rate", "temperature_celsius")


class PredictUseCase:
    """
    Orchestrates per-metric forecasts + crisis signature + service sequence analysis,
    then asks the LLM to synthesise a risk_outlook and predicted_events.
    """

    def __init__(
        self,
        repo: MetricRepository,
        llm: LLMProvider,
        risk_classifier: RiskClassifier,
        linear: LinearForecaster | None = None,
        pattern: PatternDetector | None = None,
        crisis: CrisisDetector | None = None,
        services: ServiceSequenceAnalyzer | None = None,
        history_window: int = 20,
    ):
        self._repo = repo
        self._llm = llm
        self._risk = risk_classifier
        self._linear = linear or LinearForecaster()
        self._pattern = pattern or PatternDetector(self._linear)
        self._crisis = crisis or CrisisDetector()
        self._services = services or ServiceSequenceAnalyzer()
        self._history_window = history_window

    def execute(self, anomalies: list[Anomaly]) -> tuple[dict, list[str]]:
        history = MetricSeries(self._repo.recent(self._history_window))
        errors: list[str] = []

        forecasts: dict[str, Forecast] = {}
        for metric in GRADUAL_METRICS:
            values = history.values_of(metric)
            f = self._linear.forecast(metric, values)
            if f is not None:
                forecasts[metric] = f
        for metric in REACTIVE_METRICS:
            values = history.values_of(metric)
            f = self._pattern.detect(metric, values)
            if f is not None:
                forecasts[metric] = f

        next_interval = {
            m: {
                "current_value": f.current_value,
                "predicted_value": f.predicted_value,
                "trend": f.trend,
                "risk_level": self._risk.classify(m, f.predicted_value),
                "pattern": f.pattern,
                "method": f.method,
            }
            for m, f in forecasts.items()
        }

        crisis_signal = self._crisis.evaluate(history, forecasts).to_dict()
        service_signals = {svc: sig.to_dict() for svc, sig in self._services.analyze(history).items()}

        risk_outlook = ""
        predicted_events: list[dict] = []
        try:
            risk_outlook, predicted_events = self._synthesise(
                next_interval, crisis_signal, service_signals, anomalies,
            )
        except Exception as exc:
            errors.append(f"[prediction] Outlook generation failed: {exc}")
            risk_outlook = "Prediction analysis unavailable."

        return {
            "next_interval": next_interval,
            "crisis_signal": crisis_signal,
            "service_signals": service_signals,
            "risk_outlook": risk_outlook,
            "predicted_events": predicted_events,
        }, errors

    def _synthesise(
        self,
        next_interval: dict,
        crisis_signal: dict,
        service_signals: dict,
        anomalies: list[Anomaly],
    ) -> tuple[str, list[dict]]:
        anomaly_sample = [a.to_dict() for a in anomalies[:5]]
        prompt = (
            "You are an infrastructure monitoring expert.\n\n"
            f"Metric predictions (next 30 min):\n{json.dumps(next_interval, indent=2)}\n\n"
            f"Multi-metric crisis signal:\n{json.dumps(crisis_signal, indent=2)}\n\n"
            f"Service status analysis:\n{json.dumps(service_signals, indent=2)}\n\n"
            f"Current anomalies (sample):\n{json.dumps(anomaly_sample, indent=2)}\n\n"
            "Tasks:\n"
            "1. Write a concise 2-3 sentence risk_outlook.\n"
            "2. List 0-3 specific predicted_events likely in the next 30-60 min.\n\n"
            'Return ONLY: {"risk_outlook": "...", "predicted_events": ['
            '{"event": "...", "probability": "HIGH|MEDIUM|LOW", "timeframe": "30min|60min"}]}'
        )
        parsed = self._llm.complete_json(
            system="You are an infrastructure monitoring expert. Respond with valid JSON only.",
            user=prompt,
        )
        if not isinstance(parsed, dict):
            return "", []
        return parsed.get("risk_outlook", ""), parsed.get("predicted_events", [])
