#!/usr/bin/env bash

PID_FILE=".streamlit.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No $PID_FILE found — trying to kill by process name..."
    pkill -f "streamlit run app.py" 2>/dev/null \
        && echo "App stopped." \
        || echo "No running instance found."
    exit 0
fi

PID=$(cat "$PID_FILE")
echo "Stopping Infrastructure Optimisation Dashboard (PID $PID)..."

if kill "$PID" 2>/dev/null; then
    echo "App stopped."
else
    echo "Process $PID not found — may have already exited."
fi

rm -f "$PID_FILE"
