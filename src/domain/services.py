from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from src.domain.metrics import MetricSeries


Risk = Literal["NORMAL", "WARNING", "CRITICAL"]


@dataclass(frozen=True, slots=True)
class ServiceSignal:
    service: str
    current_status: str
    recent_degradation: bool
    active_transition: bool
    issue_rate_in_history: float
    risk: Risk

    def to_dict(self) -> dict:
        return {
            "current_status": self.current_status,
            "recent_degradation": self.recent_degradation,
            "active_transition": self.active_transition,
            "issue_rate_in_history": self.issue_rate_in_history,
            "risk": self.risk,
        }


class ServiceSequenceAnalyzer:
    """
    Service status transition analyzer.

    Key insight from data analysis:
    - Database OFFLINE is independent of load (likely network/external).
    - API Gateway DEGRADED is load-driven — pairs with CPU/latency/io surge.
    Both need distinct risk communication.
    """

    SERVICES = ("database", "api_gateway", "cache")

    def analyze(self, history: MetricSeries) -> dict[str, ServiceSignal]:
        signals: dict[str, ServiceSignal] = {}

        for svc in self.SERVICES:
            statuses = [s for s in history.statuses_of(svc) if s is not None]
            if not statuses:
                continue

            current = statuses[-1]
            recent5 = statuses[-5:]
            recent_issues = [s for s in recent5 if s != "online"]
            issue_rate = sum(1 for s in statuses if s != "online") / len(statuses)
            active_transition = len(statuses) >= 2 and statuses[-2] == "online" and current != "online"

            if current == "offline":
                risk: Risk = "CRITICAL"
            elif current == "degraded":
                risk = "WARNING"
            elif active_transition or (recent_issues and issue_rate > 0.20):
                risk = "WARNING"
            else:
                risk = "NORMAL"

            signals[svc] = ServiceSignal(
                service=svc,
                current_status=current,
                recent_degradation=len(recent_issues) > 0,
                active_transition=active_transition,
                issue_rate_in_history=round(issue_rate, 3),
                risk=risk,
            )

        return signals
