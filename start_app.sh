#!/usr/bin/env bash
set -e

echo "================================================"
echo "  Infrastructure Optimisation Dashboard"
echo "================================================"
echo

if ! command -v streamlit &> /dev/null; then
    echo "ERROR: streamlit not found."
    echo "Run: pip install -r requirements.txt"
    exit 1
fi

if [ -f .streamlit.pid ] && kill -0 "$(cat .streamlit.pid)" 2>/dev/null; then
    echo "App already running (PID $(cat .streamlit.pid))."
    echo "Run ./stop_app.sh first to restart."
    exit 0
fi

# ── Database initialisation ───────────────────────────────────────────────────
INIT_DB=0

# Accept --init-db or --fresh as CLI argument
for arg in "$@"; do
    case "$arg" in
        --init-db|--fresh) INIT_DB=1 ;;
    esac
done

# If no flag given and a DB exists, ask interactively
if [ "$INIT_DB" -eq 0 ] && [ -f infrastructure.db ]; then
    echo "Une base de données existante a été détectée (infrastructure.db)."
    echo
    read -rp "Réinitialiser la base de données ? [o/N] : " answer
    case "$answer" in
        [oO]|[oO][uU][iI]) INIT_DB=1 ;;
    esac
fi

if [ "$INIT_DB" -eq 1 ]; then
    if [ -f infrastructure.db ]; then
        rm infrastructure.db
        echo "Base de données supprimée — elle sera recréée au premier run."
    else
        echo "Aucune base de données existante, elle sera créée au démarrage."
    fi
else
    [ -f infrastructure.db ] && echo "Base de données conservée."
fi
echo

# ── Start ─────────────────────────────────────────────────────────────────────
streamlit run app.py &
echo $! > .streamlit.pid

sleep 2
echo "Dashboard running at : http://localhost:8501"
echo "PID                  : $(cat .streamlit.pid)"
echo
echo "Run ./stop_app.sh to stop the server."
