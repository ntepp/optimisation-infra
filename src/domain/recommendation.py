from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


Priority = Literal["HIGH", "MEDIUM", "LOW"]


@dataclass(frozen=True, slots=True)
class Recommendation:
    priority: Priority
    action: str
    affected_metrics: list[str]
    rationale: str

    def to_dict(self) -> dict:
        return {
            "priority": self.priority,
            "action": self.action,
            "affected_metrics": list(self.affected_metrics),
            "rationale": self.rationale,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Recommendation":
        return cls(
            priority=d.get("priority", "MEDIUM"),
            action=d.get("action", ""),
            affected_metrics=list(d.get("affected_metrics", [])),
            rationale=d.get("rationale", ""),
        )
