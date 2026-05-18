from __future__ import annotations

import json

from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricSeries
from src.domain.recommendation import Recommendation
from src.ports.llm import LLMProvider
from src.ports.repository import MetricRepository


_HISTORY_KEYS = [
    "timestamp", "cpu_usage", "memory_usage", "latency_ms",
    "disk_usage", "error_rate", "temperature_celsius",
    "service_status_database", "service_status_api_gateway", "service_status_cache",
]


class RecommendUseCase:
    """LLM-driven recommendations grounded in current anomalies + recent metric history."""

    def __init__(self, repo: MetricRepository, llm: LLMProvider, history_window: int = 5):
        self._repo = repo
        self._llm = llm
        self._history_window = history_window

    def execute(self, anomalies: list[Anomaly]) -> tuple[list[Recommendation], list[str]]:
        if not anomalies:
            return [], []

        history = MetricSeries(self._repo.recent(self._history_window))
        history_slim = [
            {k: v for k, v in p.to_flat_dict().items() if k in _HISTORY_KEYS}
            for p in history
        ]
        anomaly_payload = [a.to_dict() for a in anomalies]

        prompt = (
            "You are an infrastructure optimization expert advising a French SME CTO.\n\n"
            f"Detected anomalies:\n{json.dumps(anomaly_payload, indent=2)}\n\n"
            f"Recent metric history ({self._history_window} readings):\n"
            f"{json.dumps(history_slim, indent=2)}\n\n"
            "Return a JSON object with a 'recommendations' array. Each item must have:\n"
            "  - priority: 'HIGH' | 'MEDIUM' | 'LOW'\n"
            "  - action: specific, concrete action to take\n"
            "  - affected_metrics: list of metric names this addresses\n"
            "  - rationale: 1-2 sentences linking the anomalies to the action\n\n"
            "Return ONLY the JSON object."
        )

        try:
            result = self._llm.complete_json(
                system="You are an infrastructure optimization expert. Respond with valid JSON only.",
                user=prompt,
            )
            items = result.get("recommendations", []) if isinstance(result, dict) else []
            return [Recommendation.from_dict(r) for r in items if isinstance(r, dict)], []
        except Exception as exc:
            return [], [f"[recommendation] LLM call failed: {exc}"]
