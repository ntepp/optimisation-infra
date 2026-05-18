from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.domain.anomalies import Anomaly
from src.domain.metrics import MetricPoint, TimeWindow
from src.domain.recommendation import Recommendation


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    points: list[MetricPoint]
    window: TimeWindow


@dataclass
class AnalysisReport:
    generated_at: datetime
    records_processed: int
    anomalies: list[Anomaly] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    predictions: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    mode: str = "batch"

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "mode": self.mode,
            "records_processed": self.records_processed,
            "anomalies": [a.to_dict() for a in self.anomalies],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "predictions": self.predictions,
            "errors": list(self.errors),
        }
