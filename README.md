# Infrastructure Optimisation Pipeline

Système modulaire d'analyse, de détection d'anomalies et de recommandations pour l'infrastructure technique d'une PME, développé dans le cadre d'un test technique Devoteam.

---

## Architecture

Le pipeline est orchestré avec **LangGraph** et structuré en 4 nœuds stateless. L'état est externalisé dans une base **SQLite** persistante entre les runs.

```
[Données JSON]
      │
      ▼
┌─────────────────┐
│  1. Ingestion   │  Validation Pydantic → normalisation → persistance SQLite
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  2. Détection anomalies │  Seuils par métrique + explication GPT-4o
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│  3. Recommandations      │  Analyse cross-métrique GPT-4o → actions priorisées
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│  4. Prédiction           │  Régression linéaire (métriques graduelles)
│                          │  + Détection de patterns (métriques réactives)
│                          │  + Signature de crise multi-métrique
│                          │  + Analyse séquences services
│                          │  + Synthèse GPT-4o (risk_outlook + predicted_events)
└────────┬─────────────────┘
         │
         ▼
  [Rapport JSON + Dashboard Streamlit]
```

### Stratégie de prédiction

Deux approches selon la nature de la métrique, justifiées par l'analyse du jeu de données (500 enregistrements, 10,5 jours) :

| Métriques | Méthode | Raison |
|---|---|---|
| `disk_usage`, `memory_usage`, `power_consumption_watts` | Régression linéaire | Dérive lente et progressive |
| `cpu_usage`, `latency_ms`, `io_wait`, `error_rate`, `temperature_celsius` | Détection de pattern (PRECURSOR / RISING / DECLINING / STABLE) | Spikes quasi-instantanés (91% durent 1 intervalle) — la régression ne les capte pas |

Un **signal de crise multi-métrique** détecte la signature corrélée observée dans les données : toute dégradation API Gateway coïncide systématiquement avec cpu > 85%, latency > 220ms et io_wait > 7% simultanément.

---

## Stack technique

| Composant | Choix |
|---|---|
| Orchestration pipeline | [LangGraph](https://github.com/langchain-ai/langgraph) |
| LLM | OpenAI GPT-4o |
| Validation données | Pydantic v2 |
| Persistance | SQLite (via `sqlite3`) |
| Calcul statistique | NumPy, scikit-learn |
| Dashboard | Streamlit + Plotly |
| Observabilité | LangSmith |

---

## Prérequis

- Python 3.11+
- Clé API OpenAI
- Clé API LangSmith (optionnel, pour le tracing)

---

## Installation

```bash
# 1. Cloner le dépôt
git clone <repo-url>
cd Test-Optimisation-infra

# 2. Créer et activer un environnement virtuel (recommandé)
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / Mac
source .venv/bin/activate

# 3. Installer les dépendances
pip install -r requirements.txt
```

---

## Configuration

Créer un fichier `.env` à la racine du projet :

```env
OPENAI_API_KEY=sk-...

# LangSmith (optionnel)
LANGSMITH_API_KEY=lsv2_...
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=test-optimisation-infra
```

---

## Utilisation

### Dashboard Streamlit (recommandé)

**Windows**
```bat
start_app.bat               # conserve la base de données existante
start_app.bat --init-db     # réinitialise la base de données avant démarrage
start_app.bat --fresh       # alias de --init-db

stop_app.bat                # arrête le serveur
```

**Linux / Mac**
```bash
chmod +x start_app.sh stop_app.sh   # une seule fois

./start_app.sh              # conserve la base de données existante
./start_app.sh --init-db    # réinitialise la base de données avant démarrage
./start_app.sh --fresh      # alias de --init-db

./stop_app.sh               # arrête le serveur
```

Ouvrir [http://localhost:8501](http://localhost:8501)

---

### CLI (ligne de commande)

```bash
# Analyser un seul enregistrement (index 0 = premier, souvent le plus critique)
python main.py --mode single --input docs/rapport.json --index 0

# Analyser une fenêtre de 2 heures depuis le début du fichier
python main.py --mode batch --input docs/rapport.json --window 120

# Analyser l'intégralité du fichier
python main.py --mode batch --input docs/rapport.json --all
```

Le rapport JSON est affiché sur `stdout` et sauvegardé dans `output/report_<timestamp>.json`.

---

## Format des données d'entrée

```json
{
  "timestamp": "2023-10-01T12:00:00Z",
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

---

## Format du rapport de sortie

```json
{
  "generated_at": "2026-05-16T10:30:00Z",
  "mode": "batch",
  "records_processed": 4,
  "anomalies": [
    {
      "metric": "cpu_usage",
      "value": 93.0,
      "threshold": 90.0,
      "severity": "CRITICAL",
      "explanation": "CPU à 93% indique une saturation...",
      "timestamp": "2023-10-01T12:00:00Z"
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
        "recent_degradation": true,
        "active_transition": true,
        "issue_rate_in_history": 0.134,
        "risk": "WARNING"
      }
    },
    "risk_outlook": "Le CPU et la latence sont en trajectoire ascendante...",
    "predicted_events": [
      {
        "event": "API Gateway likely to degrade further",
        "probability": "HIGH",
        "timeframe": "30min"
      }
    ]
  },
  "errors": []
}
```

---

## Structure du projet

```
Test-Optimisation-infra/
├── src/
│   ├── pipeline/
│   │   ├── graph.py                 # LangGraph StateGraph (4 nœuds)
│   │   ├── state.py                 # PipelineState TypedDict
│   │   └── nodes/
│   │       ├── ingestion.py         # Nœud 1 — validation & persistance
│   │       ├── anomaly_detection.py # Nœud 2 — seuils + explication LLM
│   │       ├── recommendation.py    # Nœud 3 — recommandations cross-métriques
│   │       ├── prediction.py        # Nœud 4 — prédiction & signaux de crise
│   │       └── _utils.py            # Nettoyage réponses LLM (markdown fences)
│   ├── db/
│   │   └── storage.py               # Interface SQLite
│   ├── models/
│   │   └── schemas.py               # Modèles Pydantic
│   └── config.py                    # Seuils d'anomalie, constantes
├── docs/
│   ├── rapport.json                 # 500 enregistrements (10,5 jours)
├── output/                          # Rapports JSON générés
├── app.py                           # Dashboard Streamlit
├── main.py                          # Entrée CLI
├── start_app.bat / start_app.sh     # Démarrage (Windows / Linux-Mac)
├── stop_app.bat  / stop_app.sh      # Arrêt   (Windows / Linux-Mac)
├── requirements.txt
└── .env                             # Clés API (non versionné)
```

---

## Observabilité LangSmith

Quand `LANGCHAIN_TRACING_V2=true` est défini, chaque run du pipeline est automatiquement tracé dans le dashboard LangSmith sous le projet `test-optimisation-infra`. Chaque nœud LangGraph apparaît comme un span distinct avec ses inputs/outputs et les appels GPT-4o détaillés.
