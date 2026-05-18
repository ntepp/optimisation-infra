"""
Streamlit dashboard for the Infrastructure Optimisation Pipeline.

Run with:
    streamlit run app.py
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.adapters.inbound.runner import run_analysis
from src.adapters.outbound.persistence.sqlite_repo import SqliteMetricRepository
from src.adapters.outbound.sources.in_memory import InMemorySource
from src.adapters.outbound.sources.json_file import JsonFileSource
from src.domain.metrics import MetricPoint, TimeWindow, _parse_utc
from src.infrastructure.config import ANOMALY_THRESHOLDS, Settings

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Infra Optimisation",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.metric-card {
    background: #1e1e2e; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 10px;
    border-left: 5px solid #888;
}
.metric-card.critical { border-left-color: #ef4444; }
.metric-card.warning  { border-left-color: #f59e0b; }
.badge {
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.05em;
}
.badge-high     { background: #ef4444; color: white; }
.badge-medium   { background: #f59e0b; color: white; }
.badge-low      { background: #22c55e; color: white; }
.badge-critical { background: #ef4444; color: white; }
.badge-warning  { background: #f59e0b; color: white; }
.rec-card {
    background: #1e1e2e; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
SEVERITY_COLOR = {"CRITICAL": "#ef4444", "WARNING": "#f59e0b", "NORMAL": "#22c55e"}
TREND_ICON     = {"increasing": "📈", "decreasing": "📉", "stable": "➡️"}
RISK_ICON      = {"CRITICAL": "🔴", "WARNING": "🟡", "NORMAL": "🟢"}
PRIORITY_ICON  = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}

SETTINGS = Settings.from_env()


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_all_records(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def load_points_from_file(path: str) -> list[MetricPoint]:
    return list(JsonFileSource(path).fetch(None))


def filter_points(points: list[MetricPoint], mode: str, index: int,
                  date_from: datetime, date_to: datetime, all_rec: bool) -> list[MetricPoint]:
    if mode == "single":
        idx = min(index, len(points) - 1) if points else 0
        return [points[idx]] if points else []
    if all_rec:
        return points
    return [p for p in points if date_from <= p.timestamp <= date_to]


def run_pipeline(points: list[MetricPoint], mode: str) -> dict:
    return run_analysis(
        source=InMemorySource(points),
        settings=SETTINGS,
        window=None,
        mode_label=mode,
    )


def save_report(report: dict) -> Path:
    out_dir = Path(SETTINGS.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    p = out_dir / f"report_{ts}.json"
    p.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return p


def load_latest_report() -> dict | None:
    reports = sorted(Path(SETTINGS.output_dir).glob("report_*.json"), reverse=True)
    if not reports:
        return None
    return json.loads(reports[0].read_text(encoding="utf-8"))


def points_to_dataframe(points: list[MetricPoint]) -> pd.DataFrame:
    return pd.DataFrame([p.to_flat_dict() for p in points])


def _datetime_picker(label: str, default_dt: datetime,
                     min_dt: datetime, max_dt: datetime, key: str) -> datetime:
    col_d, col_t = st.columns([2, 1])
    with col_d:
        d = st.date_input(label, value=default_dt.date(),
                          min_value=min_dt.date(), max_value=max_dt.date(),
                          key=f"{key}_date")
    with col_t:
        t = st.time_input("Heure", value=default_dt.time(),
                          key=f"{key}_time", step=3600)
    return datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=timezone.utc)


# ── Session state init ────────────────────────────────────────────────────────
if "report" not in st.session_state:
    st.session_state.report = load_latest_report()

REPO = SqliteMetricRepository(SETTINGS.db_path)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/server.png", width=64)
    st.title("Infra Optimisation")
    st.divider()

    st.subheader("⚙️ Pipeline Config")
    mode = st.radio("Processing mode", ["single", "batch"], horizontal=True)
    input_path = st.text_input("JSON metrics file", value="docs/rapport.json")

    data_bounds: tuple[datetime, datetime] | None = None
    _points: list[MetricPoint] = []
    if Path(input_path).exists():
        try:
            _points = load_points_from_file(input_path)
            if _points:
                ts = [p.timestamp for p in _points]
                data_bounds = (min(ts), max(ts))
        except Exception:
            data_bounds = None

    if mode == "single":
        rec_index = st.number_input("Record index", min_value=0, value=0, step=1)
        date_from = date_to = datetime.now(timezone.utc)
        all_records = False

    else:
        all_records = st.checkbox("Process all records", value=False)

        if not all_records and data_bounds:
            st.markdown("**📅 Période**")
            date_from = _datetime_picker("Du", data_bounds[0],
                                         data_bounds[0], data_bounds[1], "sb_from")
            date_to   = _datetime_picker("Au", data_bounds[1],
                                         data_bounds[0], data_bounds[1], "sb_to")
            n_in_range = sum(1 for p in _points if date_from <= p.timestamp <= date_to)
            st.caption(f"{n_in_range} enregistrement(s) dans la plage sélectionnée")
        else:
            date_from = data_bounds[0] if data_bounds else datetime.now(timezone.utc)
            date_to   = data_bounds[1] if data_bounds else datetime.now(timezone.utc)

        rec_index = 0

    st.divider()
    run_btn = st.button("▶️  Run Pipeline", type="primary", width='stretch')
    st.divider()
    st.caption("LangSmith tracing active when LANGCHAIN_TRACING_V2=true")

# ── Run pipeline ──────────────────────────────────────────────────────────────
if run_btn:
    if not Path(input_path).exists():
        st.error(f"File not found: `{input_path}`")
    else:
        points = load_points_from_file(input_path)
        selected = filter_points(points, mode, rec_index, date_from, date_to, all_records)
        if not selected:
            st.warning("No records match the selected period.")
        else:
            with st.spinner(f"Running pipeline on {len(selected)} record(s)…"):
                report = run_pipeline(selected, mode)
            st.session_state.report = report
            saved = save_report(report)
            st.success(f"Pipeline complete — {len(selected)} records processed. Report saved to `{saved}`")

# ── Main dashboard ────────────────────────────────────────────────────────────
report = st.session_state.report

st.title("🖥️  Infrastructure Optimisation Dashboard")

if report is None:
    st.info("Configure the pipeline in the sidebar and click **▶️ Run Pipeline** to start.")
    hist_points = REPO.recent(50)
    if hist_points:
        st.subheader("📊 Recent Metric History (from DB)")
        df = points_to_dataframe(hist_points)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.sort_values("timestamp")
        fig = go.Figure()
        for m in ["cpu_usage", "memory_usage", "latency_ms", "temperature_celsius", "error_rate"]:
            if m in df.columns:
                fig.add_trace(go.Scatter(x=df["timestamp"], y=df[m], mode="lines", name=m))
        fig.update_layout(title="Historical Metrics", template="plotly_dark", height=400,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, width='stretch')
    st.stop()

# ── KPI bar ───────────────────────────────────────────────────────────────────
anomalies       = report.get("anomalies", [])
recommendations = report.get("recommendations", [])
predictions     = report.get("predictions", {})
errors          = report.get("errors", [])

critical_count = sum(1 for a in anomalies if a.get("severity") == "CRITICAL")
warning_count  = sum(1 for a in anomalies if a.get("severity") == "WARNING")
overall_risk   = "CRITICAL" if critical_count else "WARNING" if warning_count else "NORMAL"

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Records Processed", report.get("records_processed", 0))
c2.metric("🔴 Critical Anomalies", critical_count)
c3.metric("🟡 Warnings", warning_count)
c4.metric("💡 Recommendations", len(recommendations))
c5.metric("Overall Risk", overall_risk)

st.caption(
    f"Generated at {report.get('generated_at', '—')}  ·  Mode: **{report.get('mode', '—')}**"
    + (f"  ·  ⚠️ {len(errors)} error(s)" if errors else "")
)
st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_anom, tab_recs, tab_pred, tab_hist, tab_raw = st.tabs(
    ["🚨 Anomalies", "💡 Recommendations", "🔮 Predictions", "📊 History", "🗂️ Raw Report"]
)

# ── Anomalies ─────────────────────────────────────────────────────────────────
with tab_anom:
    if not anomalies:
        st.success("✅ No anomalies detected in this run.")
    else:
        st.markdown(f"**{len(anomalies)} anomaly/anomalies detected.**")
        for severity in ("CRITICAL", "WARNING"):
            group = [a for a in anomalies if a.get("severity") == severity]
            if not group:
                continue
            icon = "🔴" if severity == "CRITICAL" else "🟡"
            st.markdown(f"#### {icon} {severity} ({len(group)})")
            cols = st.columns(min(len(group), 2))
            for i, a in enumerate(group):
                with cols[i % 2]:
                    st.markdown(
                        f"""<div class="metric-card {severity.lower()}">
                            <b>{a.get('metric','')}</b>
                            &nbsp;<span class="badge badge-{severity.lower()}">{severity}</span><br/>
                            <span style="font-size:1.4rem;font-weight:700">{a.get('value','')}</span>
                            <span style="color:#aaa;font-size:0.85rem">&nbsp;/ seuil: {a.get('threshold','')}</span><br/>
                            <span style="color:#ccc;font-size:0.85rem">{a.get('explanation','')}</span><br/>
                            <span style="color:#666;font-size:0.75rem">{a.get('timestamp','')}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        numeric_anom = [a for a in anomalies if isinstance(a.get("value"), (int, float))]
        if numeric_anom:
            df_a = pd.DataFrame(numeric_anom)
            fig = go.Figure(go.Bar(
                x=df_a["metric"], y=df_a["value"],
                marker_color=[SEVERITY_COLOR.get(s, "#888") for s in df_a["severity"]],
                text=df_a["severity"], textposition="outside",
            ))
            fig.update_layout(title="Anomalous Metric Values", template="plotly_dark",
                              height=350, showlegend=False, yaxis_title="Value")
            st.plotly_chart(fig, width='stretch')

# ── Recommendations ───────────────────────────────────────────────────────────
with tab_recs:
    if not recommendations:
        st.info(
            "No recommendations for this run.\n\n"
            "This happens when: no anomalies were detected, or the pipeline ran on a single "
            "clean record. Try a batch run covering a period with anomalies."
        )
    else:
        priority_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        for rec in sorted(recommendations, key=lambda r: priority_order.get(r.get("priority", "LOW"), 3)):
            p = rec.get("priority", "LOW")
            affected = ", ".join(rec.get("affected_metrics", []))
            st.markdown(
                f"""<div class="rec-card">
                    <span class="badge badge-{p.lower()}">{PRIORITY_ICON.get(p,'')} {p}</span>
                    <p style="font-size:1rem;font-weight:600;margin:8px 0 4px">{rec.get('action','')}</p>
                    <p style="color:#aaa;font-size:0.875rem;margin:0 0 6px">{rec.get('rationale','')}</p>
                    <span style="color:#666;font-size:0.78rem">Affects: {affected}</span>
                </div>""",
                unsafe_allow_html=True,
            )

# ── Predictions ───────────────────────────────────────────────────────────────
with tab_pred:
    next_interval    = predictions.get("next_interval", {})
    risk_outlook     = predictions.get("risk_outlook", "")
    crisis_signal    = predictions.get("crisis_signal", {})
    service_signals  = predictions.get("service_signals", {})
    predicted_events = predictions.get("predicted_events", [])

    if crisis_signal.get("detected"):
        sev = crisis_signal.get("severity", "WARNING")
        conf = int(crisis_signal.get("confidence", 0) * 100)
        icon = "🔴" if sev == "CRITICAL" else "🟡"
        if sev == "CRITICAL":
            st.error(f"{icon} **Crisis signature detected** (confidence {conf}%) — "
                     f"{crisis_signal.get('description','')}")
        else:
            st.warning(f"{icon} **Crisis precursor detected** (confidence {conf}%) — "
                       f"{crisis_signal.get('description','')}")

    if risk_outlook and risk_outlook != "Prediction analysis unavailable.":
        st.info(f"**Risk Outlook:** {risk_outlook}")

    if predicted_events:
        st.markdown("#### 🎯 Predicted Events (next 30–60 min)")
        prob_color = {"HIGH": "#ef4444", "MEDIUM": "#f59e0b", "LOW": "#22c55e"}
        for ev in predicted_events:
            prob = ev.get("probability", "LOW")
            st.markdown(
                f"""<div class="rec-card" style="border-left:4px solid {prob_color.get(prob,'#888')}">
                    <span class="badge badge-{prob.lower()}">{prob}</span>
                    &nbsp;<span style="color:#aaa;font-size:0.8rem">{ev.get('timeframe','')}</span><br/>
                    <span style="font-size:0.95rem">{ev.get('event','')}</span>
                </div>""",
                unsafe_allow_html=True,
            )

    if service_signals:
        st.markdown("#### 🔌 Service Risk Signals")
        svc_cols = st.columns(len(service_signals))
        svc_risk_color = {"CRITICAL": "critical", "WARNING": "warning", "NORMAL": "normal"}
        for i, (svc, sig) in enumerate(service_signals.items()):
            with svc_cols[i]:
                risk = sig.get("risk", "NORMAL")
                status = sig.get("current_status", "?")
                rate = sig.get("issue_rate_in_history", 0)
                transition = sig.get("active_transition", False)
                st.markdown(
                    f"""<div class="metric-card {svc_risk_color.get(risk,'normal')}">
                        <b>{svc.replace('_',' ').title()}</b><br/>
                        <span style="font-size:1.2rem;font-weight:700">{status}</span><br/>
                        <span style="color:#aaa;font-size:0.8rem">Issue rate: {rate:.0%}</span><br/>
                        {"⚡ <span style='color:#f59e0b;font-size:0.8rem'>Active transition</span>" if transition else ""}
                    </div>""",
                    unsafe_allow_html=True,
                )

    if not next_interval:
        st.warning(
            "No metric predictions yet.\n\n"
            "Need at least **2 records in the database** to compute trends. "
            "Run in batch mode to populate history."
        )
    else:
        st.markdown("#### 📊 Metric Predictions (next 30 min)")
        metrics_p      = list(next_interval.keys())
        current_vals   = [next_interval[m]["current_value"]  for m in metrics_p]
        predicted_vals = [next_interval[m]["predicted_value"] for m in metrics_p]
        risk_levels    = [next_interval[m]["risk_level"]      for m in metrics_p]

        fig = go.Figure()
        fig.add_trace(go.Bar(name="Current", x=metrics_p, y=current_vals,
                             marker_color="#6366f1"))
        fig.add_trace(go.Bar(name="Predicted +30 min", x=metrics_p, y=predicted_vals,
                             marker_color=[SEVERITY_COLOR.get(r, "#888") for r in risk_levels]))
        fig.update_layout(barmode="group", title="Current vs Predicted Values",
                          template="plotly_dark", height=400,
                          legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, width='stretch')

        PATTERN_ICON = {
            "PRECURSOR": "⚠️", "RISING": "📈", "DECLINING": "📉",
            "STABLE": "➡️", "LINEAR": "📐", "INSUFFICIENT_DATA": "❓",
        }
        rows = [{
            "Metric":    m,
            "Current":   next_interval[m]["current_value"],
            "Predicted": next_interval[m]["predicted_value"],
            "Δ":         round(next_interval[m]["predicted_value"] - next_interval[m]["current_value"], 2),
            "Pattern":   PATTERN_ICON.get(next_interval[m].get("pattern",""), "") + " " + next_interval[m].get("pattern","—"),
            "Trend":     TREND_ICON.get(next_interval[m]["trend"], "") + " " + next_interval[m]["trend"],
            "Risk":      RISK_ICON.get(next_interval[m]["risk_level"], "") + " " + next_interval[m]["risk_level"],
        } for m in metrics_p]
        st.dataframe(pd.DataFrame(rows).set_index("Metric"), width='stretch')

# ── History ───────────────────────────────────────────────────────────────────
with tab_hist:
    hist_points = REPO.recent(500)

    if not hist_points:
        st.info("No historical data yet. Run the pipeline first.")
    else:
        df_h = points_to_dataframe(hist_points)
        df_h["timestamp"] = pd.to_datetime(df_h["timestamp"], utc=True)
        df_h = df_h.sort_values("timestamp")

        st.markdown("### 📅 Filtrer la période (source : infrastructure.db)")
        h_min_dt = df_h["timestamp"].min().to_pydatetime()
        h_max_dt = df_h["timestamp"].max().to_pydatetime()

        h_from = _datetime_picker("Du", h_min_dt, h_min_dt, h_max_dt, "hist_from")
        h_to   = _datetime_picker("Au", h_max_dt, h_min_dt, h_max_dt, "hist_to")

        mask = (df_h["timestamp"] >= pd.Timestamp(h_from)) & \
               (df_h["timestamp"] <= pd.Timestamp(h_to))
        df_h = df_h[mask]
        st.caption(
            f"**{len(df_h)}** enregistrement(s) — "
            f"{h_from:%Y-%m-%d %H:%M} → {h_to:%Y-%m-%d %H:%M} (infrastructure.db)"
        )

        if df_h.empty:
            st.warning("No records in this period.")
        else:
            metric_opts = ["cpu_usage", "memory_usage", "latency_ms",
                           "temperature_celsius", "error_rate", "disk_usage", "io_wait"]
            sel_metrics = st.multiselect("Metrics to display", options=metric_opts,
                                         default=["cpu_usage", "memory_usage", "latency_ms"])

            if sel_metrics:
                fig = go.Figure()
                for m in sel_metrics:
                    if m not in df_h.columns:
                        continue
                    fig.add_trace(go.Scatter(x=df_h["timestamp"], y=df_h[m],
                                            mode="lines+markers", name=m, line=dict(width=2)))
                    thr = ANOMALY_THRESHOLDS.get(m, {})
                    if "critical" in thr:
                        fig.add_hline(y=thr["critical"], line_dash="dash",
                                      line_color="#ef4444",
                                      annotation_text=f"{m} CRITICAL",
                                      annotation_position="bottom right")
                    if "warning" in thr:
                        fig.add_hline(y=thr["warning"], line_dash="dot",
                                      line_color="#f59e0b",
                                      annotation_text=f"{m} WARNING",
                                      annotation_position="top right")
                fig.update_layout(title="Metric History with Thresholds",
                                  template="plotly_dark", height=460,
                                  legend=dict(orientation="h", yanchor="bottom", y=1.02),
                                  xaxis_title="Timestamp")
                st.plotly_chart(fig, width='stretch')

            svc_cols = [c for c in df_h.columns if c.startswith("service_status_")]
            if svc_cols:
                st.markdown("#### Service Status Timeline")
                status_map = {"online": 1, "degraded": 0.5, "offline": 0}
                fig2 = go.Figure()
                for col in svc_cols:
                    svc = col.replace("service_status_", "")
                    fig2.add_trace(go.Scatter(
                        x=df_h["timestamp"],
                        y=[status_map.get(v, None) for v in df_h[col]],
                        mode="lines+markers", name=svc,
                        line=dict(shape="hv", width=2),
                    ))
                fig2.update_layout(
                    template="plotly_dark", height=260,
                    yaxis=dict(tickvals=[0, 0.5, 1], ticktext=["offline", "degraded", "online"]),
                    legend=dict(orientation="h"),
                )
                st.plotly_chart(fig2, width='stretch')

# ── Raw Report ────────────────────────────────────────────────────────────────
with tab_raw:
    if errors:
        st.warning(f"**{len(errors)} error(s) during run:**")
        for e in errors:
            st.code(e)
    st.download_button(
        label="⬇️  Download Report JSON",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name=f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )
    st.json(report)
