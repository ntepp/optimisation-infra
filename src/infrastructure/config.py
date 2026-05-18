"""
Application settings. Loaded once at startup and injected through the container.

Environment variables override defaults. `.env` is auto-loaded via python-dotenv
in the CLI/Streamlit entry points before Settings is instantiated.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field


# ── Anomaly thresholds ────────────────────────────────────────────────────────

ANOMALY_THRESHOLDS: dict[str, dict[str, float]] = {
    "cpu_usage":            {"warning": 80.0,  "critical": 90.0},
    "memory_usage":         {"warning": 80.0,  "critical": 88.0},
    "latency_ms":           {"warning": 220.0, "critical": 320.0},
    "temperature_celsius":  {"warning": 75.0,  "critical": 83.0},
    "error_rate":           {"warning": 0.05,  "critical": 0.10},
    "disk_usage":           {"warning": 75.0,  "critical": 88.0},
    "io_wait":              {"warning": 7.0,   "critical": 11.0},
}

SERVICE_STATUS_SEVERITY: dict[str, str | None] = {
    "online":   None,
    "degraded": "WARNING",
    "offline":  "CRITICAL",
}


@dataclass(frozen=True, slots=True)
class Settings:
    """Application-wide configuration, populated from env vars with sensible defaults."""

    # LLM
    model_name: str = "gpt-4o"
    openai_api_key: str | None = None

    # Persistence
    db_path: str = "infrastructure.db"

    # Output
    output_dir: str = "output"

    # History windows for use-cases
    history_anomaly: int = 10
    history_recommendation: int = 5
    history_prediction: int = 20

    # Anomaly thresholds (kept in module scope to avoid env-var explosion)
    thresholds: dict[str, dict[str, float]] = field(default_factory=lambda: dict(ANOMALY_THRESHOLDS))
    service_status_severity: dict[str, str | None] = field(default_factory=lambda: dict(SERVICE_STATUS_SEVERITY))

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            model_name=os.getenv("MODEL_NAME", "gpt-4o"),
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            db_path=os.getenv("DB_PATH", "infrastructure.db"),
            output_dir=os.getenv("OUTPUT_DIR", "output"),
            history_anomaly=int(os.getenv("HISTORY_WINDOW_ANOMALY", "10")),
            history_recommendation=int(os.getenv("HISTORY_WINDOW_RECOMMENDATION", "5")),
            history_prediction=int(os.getenv("HISTORY_WINDOW_PREDICTION", "20")),
        )
