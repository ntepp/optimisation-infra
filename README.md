# Infrastructure Optimisation Pipeline

Système d'analyse, de détection d'anomalies et de recommandations pour l'infrastructure technique d'une PME, développé dans le cadre d'un test technique Devoteam.

Construit sur une **architecture hexagonale (port-adapter)** avec **LangGraph** comme orchestrateur.

---

## Architecture

```
                    ┌─────────── INBOUND ───────────┐
                    │  CLI (main.py) · Streamlit     │
                    └──────────────┬────────────────┘
                                   │
                    ┌──────────────▼────────────────┐
                    │       APPLICATION              │
                    │  IngestMetrics · Detect        │
                    │  Recommend · Predict           │
                    │  AnalyzeBatchUseCase (façade)  │
                    └──────┬──────────────┬──────────┘
                           │              │
                    ┌──────▼──────────────▼──────────┐
                    │      DOMAINE (zéro I/O)         │
                    │  MetricPoint · TimeWindow       │
                    │  ThresholdEvaluator             │
                    │  LinearForecaster               │
                    │  PatternDetector                │
                    │  CrisisDetector                 │
                    │  ServiceSequenceAnalyzer        │
                    └──────────────────────────────────┘
                           ▲              ▲
              PORTS (Protocol — dépendances inversées)
           ┌───────────────┴──┐  ┌────────┴────────────┐
           │  MetricSource    │  │  MetricRepository   │
           │  LLMProvider     │  │  AnomalyRepository  │
           │  ReportSink      │  │  Clock              │
           └──────┬───────────┘  └────────┬────────────┘
                  │                       │
           ┌──────▼───── OUTBOUND ────────▼────────────┐
           │  JsonFileSource · StdinJsonSource          │
           │  InlineJsonSource · InMemorySource         │
           │  SqliteRepository · InMemoryRepository     │
           │  OpenAIProvider · NullLLMProvider          │
           │  JsonFileSink · StdoutSink                 │
           └────────────────────────────────────────────┘
```

### Pipeline LangGraph (4 nœuds)

```
[Source] → ingestion → anomaly → recommend → predict → [Rapport JSON]
```

Chaque nœud délègue entièrement à son use-case — aucune logique métier dans le pipeline.

### Stratégie de prédiction

| Métriques | Méthode | Raison |
|---|---|---|
| `disk_usage`, `memory_usage`, `power_consumption_watts` | Régression linéaire | Dérive lente et progressive |
| `cpu_usage`, `latency_ms`, `io_wait`, `error_rate`, `temperature_celsius` | Détection de pattern (PRECURSOR / RISING / DECLINING / STABLE) | Spikes quasi-instantanés — la régression ne les capte pas |

Un **signal de crise multi-métrique** détecte la signature corrélée : `cpu > 85%` + `latency > 220ms` + `io_wait > 7%` simultanément.

---

## Stack technique

| Composant | Choix |
|---|---|
| Orchestration pipeline | LangGraph |
| LLM | OpenAI GPT-4o |
| Persistance | SQLite (`sqlite3`) |
| Calcul statistique | NumPy, scikit-learn |
| Dashboard | Streamlit + Plotly |
| Observabilité | LangSmith |
| Tests | pytest (67 tests, aucune clé API requise) |

---

## Prérequis

- Python 3.11+
- Clé API OpenAI
- Clé API LangSmith (optionnel — tracing)

---

## Installation

```bash
git clone https://github.com/ntepp/optimisation-infra.git
cd optimisation-infra

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Configuration

Copier `.env.example` en `.env` et renseigner les clés :

```bash
cp .env.example .env
```

```env
OPENAI_API_KEY=sk-...
MODEL_NAME=gpt-4o

# LangSmith (optionnel)
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=test-optimisation-infra

# Persistance et sorties
DB_PATH=infrastructure.db
OUTPUT_DIR=output

# Fenêtres d'historique (use-cases)
HISTORY_WINDOW_ANOMALY=10
HISTORY_WINDOW_RECOMMENDATION=5
HISTORY_WINDOW_PREDICTION=20
```

---

## Utilisation

### Dashboard Streamlit (recommandé)

**Windows**
```bat
start_app.bat           # conserve la base existante
start_app.bat --init-db # réinitialise la base avant démarrage
stop_app.bat
```

**Linux / Mac**
```bash
chmod +x start_app.sh stop_app.sh
./start_app.sh
./stop_app.sh
```

Ouvrir [http://localhost:8501](http://localhost:8501)

---

### CLI

**Source fichier (défaut)**
```bash
python main.py --source file --input docs/rapport.json
python main.py --source file --input docs/rapport.json --window 120
python main.py --source file --input docs/rapport.json --all
python main.py --source file --input docs/rapport.json --index 0
```

**Source stdin (pipe)**
```bash
cat docs/rapport.json | python main.py --source stdin
echo '{"timestamp":"2026-05-18T12:00:00Z","cpu_usage":92,...}' | python main.py --source stdin
```

**Source inline (argument)**
```bash
python main.py --source inline --json '{"timestamp":"2026-05-18T12:00:00Z","cpu_usage":92,...}'
```

Le rapport JSON est affiché sur `stdout` et sauvegardé dans `output/report_<timestamp>.json`.

---

## Tests

```bash
pytest -q
```

67 tests couvrant le domaine, les adapters et le pipeline end-to-end. Aucune clé OpenAI requise — le `NullLLMProvider` remplace le LLM réel.

---

## Format des données d'entrée

```json
{
  "timestamp": "2026-05-18T12:00:00Z",
  "cpu_usage": 85,
  "memory_usage": 70,
  "latency_ms": 250,
  "disk_usage": 65,
  "network_in_kbps": 1200,
  "network_out_kbps": 900,
  "io_wait": 5,
  "thread_count": 150,
  "active_connections": 45,
  "error_rate": 0.02,
  "uptime_seconds": 360000,
  "temperature_celsius": 65,
  "power_consumption_watts": 250,
  "service_status": {
    "database": "online",
    "api_gateway": "degraded",
    "cache": "online"
  }
}
```

Les sources acceptent un objet unique ou une liste d'objets.

---

## Format du rapport de sortie

```json
{
  "generated_at": "2026-05-18T12:30:00Z",
  "mode": "batch",
  "records_processed": 4,
  "anomalies": [
    {
      "metric": "cpu_usage",
      "value": 93.0,
      "threshold": 90.0,
      "severity": "CRITICAL",
      "explanation": "CPU à 93% indique une saturation...",
      "timestamp": "2026-05-18T12:00:00Z"
    }
  ],
  "recommendations": [
    {
      "priority": "HIGH",
      "action": "Activer le scaling horizontal",
      "affected_metrics": ["cpu_usage", "latency_ms"],
      "rationale": "La saturation CPU couplée à la latence élevée..."
    }
  ],
  "predictions": {
    "next_interval": {
      "cpu_usage": {
        "current_value": 93.0,
        "predicted_value": 95.2,
        "trend": "increasing",
        "risk_level": "CRITICAL",
        "pattern": "PRECURSOR",
        "method": "pattern_detection"
      }
    },
    "crisis_signal": {
      "detected": true,
      "severity": "CRITICAL",
      "confidence": 0.9,
      "description": "Crisis signature active and escalating"
    },
    "service_signals": {
      "api_gateway": {
        "current_status": "degraded",
        "active_transition": true,
        "issue_rate_in_history": 0.134,
        "risk": "WARNING"
      }
    },
    "risk_outlook": "Le CPU et la latence sont en trajectoire ascendante...",
    "predicted_events": []
  },
  "errors": []
}
```

---

## Structure du projet

```
optimisation-infra/
├── src/
│   ├── domain/              # Logique métier pure, zéro I/O
│   │   ├── metrics.py       # MetricPoint, MetricSeries, TimeWindow
│   │   ├── anomalies.py     # Anomaly, ThresholdEvaluator
│   │   ├── forecasting.py   # LinearForecaster, PatternDetector, RiskClassifier
│   │   ├── crisis.py        # CrisisDetector, CrisisSignature
│   │   ├── services.py      # ServiceSequenceAnalyzer, ServiceSignal
│   │   └── recommendation.py
│   ├── ports/               # Interfaces (Protocol)
│   │   ├── sources.py       # MetricSource
│   │   ├── repository.py    # MetricRepository, AnomalyRepository
│   │   ├── llm.py           # LLMProvider
│   │   ├── sinks.py         # ReportSink
│   │   └── clock.py         # Clock
│   ├── application/
│   │   ├── dto.py           # AnalysisRequest, AnalysisReport
│   │   └── use_cases/
│   │       ├── ingest_metrics.py
│   │       ├── detect_anomalies.py
│   │       ├── recommend.py
│   │       ├── predict.py
│   │       └── analyze_batch.py
│   ├── adapters/
│   │   ├── inbound/
│   │   │   ├── cli.py       # Parsing args, entrée CLI
│   │   │   └── runner.py    # run_analysis() — partagé CLI + Streamlit
│   │   └── outbound/
│   │       ├── sources/     # JsonFile · Stdin · Inline · InMemory
│   │       ├── persistence/ # Sqlite · InMemory repos
│   │       ├── llm/         # OpenAI · Null providers
│   │       └── sinks/       # JsonFile · Stdout
│   └── infrastructure/
│       ├── config.py        # Settings (env vars + defaults)
│       ├── container.py     # Composition root — câblage DI
│       └── pipeline_graph.py# LangGraph StateGraph
├── tests/                   # 67 tests, pytest
├── docs/
│   └── rapport.json         # 500 enregistrements de démonstration
├── app.py                   # Dashboard Streamlit
├── main.py                  # Entrée CLI (~15 lignes)
├── start_app.bat / .sh
├── stop_app.bat  / .sh
├── requirements.txt
├── .env.example
└── .gitignore
```

---

## Observabilité

Quand `LANGCHAIN_TRACING_V2=true`, chaque run est tracé dans LangSmith sous le projet `test-optimisation-infra`. Chaque nœud LangGraph apparaît comme un span distinct avec ses inputs/outputs et les appels GPT-4o détaillés.
