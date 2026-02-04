import streamlit as st
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# -----------------------
# Config
# -----------------------
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="VizLab - Compare Signals",
    layout="wide"
)

st.title("Compare Two Signals")

# -----------------------
# API Helper
# -----------------------
def api_get(path, params=None):
    """Fetch data from backend API."""
    try:
        r = requests.get(f"{API_BASE}{path}", params=params)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        st.stop()


# -----------------------
# Signal Fetch
# -----------------------
def fetch_signal(device, workload, run, metric, window_size=1):
    """Fetch signal from backend API."""
    signal = api_get(
        "/signal",
        {
            "device": device,
            "workload": workload,
            "run": run,
            "metric": metric,
            "window_size": window_size,
        }
    )
    return signal


# -----------------------
# Sidebar Controls
# -----------------------
st.sidebar.header("Signal A")

devices_a = api_get("/devices")
device_a = st.sidebar.selectbox(
    "Device A",
    devices_a,
    key="device_a"
)

workloads_a = api_get("/workloads", {"device": device_a})
workload_a = st.sidebar.selectbox(
    "Workload A",
    workloads_a,
    key="workload_a"
)

runs_a = api_get(
    "/runs",
    {
        "device": device_a,
        "workload": workload_a,
    }
)
run_a = st.sidebar.selectbox(
    "Run A",
    runs_a,
    key="run_a"
)

metrics_a = api_get("/metrics", {"device": device_a})
metric_a = st.sidebar.selectbox(
    "Metric A",
    metrics_a,
    key="metric_a"
)

st.sidebar.divider()

st.sidebar.header("Signal B")

devices_b = api_get("/devices")
device_b = st.sidebar.selectbox(
    "Device B",
    devices_b,
    key="device_b"
)

workloads_b = api_get("/workloads", {"device": device_b})
workload_b = st.sidebar.selectbox(
    "Workload B",
    workloads_b,
    key="workload_b"
)

runs_b = api_get(
    "/runs",
    {
        "device": device_b,
        "workload": workload_b,
    }
)
run_b = st.sidebar.selectbox(
    "Run B",
    runs_b,
    key="run_b"
)

metrics_b = api_get("/metrics", {"device": device_b})
metric_b = st.sidebar.selectbox(
    "Metric B",
    metrics_b,
    key="metric_b"
)

load_clicked = st.sidebar.button("Load signals")


# -----------------------
# Fetch and Plot
# -----------------------
if load_clicked:
    signal_a = fetch_signal(device_a, workload_a, run_a, metric_a, window_size=1)
    signal_b = fetch_signal(device_b, workload_b, run_b, metric_b, window_size=1)
    st.session_state.signal_a = signal_a
    st.session_state.signal_b = signal_b

if "signal_a" not in st.session_state or "signal_b" not in st.session_state:
    st.info("Select parameters for both signals and click **Load signals**")
    st.stop()

signal_a = st.session_state.signal_a
signal_b = st.session_state.signal_b

x_a = signal_a["time"]["values"]
y_a = signal_a["values"]
labels_a = signal_a["labels"]["values"]

x_b = signal_b["time"]["values"]
y_b = signal_b["values"]
labels_b = signal_b["labels"]["values"]

# Truncate to min length
min_len = min(len(x_a), len(x_b))
x_a = x_a[:min_len]
y_a = y_a[:min_len]
labels_a = labels_a[:min_len]

x_b = x_b[:min_len]
y_b = y_b[:min_len]
labels_b = labels_b[:min_len]

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    subplot_titles=(
        f"{device_a}::{metric_a} (A)",
        f"{device_b}::{metric_b} (B)"
    ),
    vertical_spacing=0.12,
)

# Signal A trace in row 1
fig.add_trace(
    go.Scatter(
        x=x_a,
        y=y_a,
        mode="lines",
        name=f"{device_a}::{metric_a} (A)",
        line=dict(width=2, color="blue"),
    ),
    row=1,
    col=1
)

# Signal B trace in row 2
fig.add_trace(
    go.Scatter(
        x=x_b,
        y=y_b,
        mode="lines",
        name=f"{device_b}::{metric_b} (B)",
        line=dict(width=2, color="green"),
    ),
    row=2,
    col=1
)

# Attack shading for Signal A (red) in row 1
in_attack_a = False
start_a = None
for i, v in enumerate(labels_a):
    if v == 1 and not in_attack_a:
        start_a = i
        in_attack_a = True
    elif v == 0 and in_attack_a:
        fig.add_vrect(
            x0=start_a,
            x1=i,
            fillcolor="red",
            opacity=0.15,
            layer="below",
            line_width=0,
            row=1,
            col=1,
        )
        in_attack_a = False

if in_attack_a:
    fig.add_vrect(
        x0=start_a,
        x1=len(labels_a),
        fillcolor="red",
        opacity=0.15,
        layer="below",
        line_width=0,
        row=1,
        col=1,
    )

# Attack shading for Signal B (orange) in row 2
in_attack_b = False
start_b = None
for i, v in enumerate(labels_b):
    if v == 1 and not in_attack_b:
        start_b = i
        in_attack_b = True
    elif v == 0 and in_attack_b:
        fig.add_vrect(
            x0=start_b,
            x1=i,
            fillcolor="orange",
            opacity=0.15,
            layer="below",
            line_width=0,
            row=2,
            col=1,
        )
        in_attack_b = False

if in_attack_b:
    fig.add_vrect(
        x0=start_b,
        x1=len(labels_b),
        fillcolor="orange",
        opacity=0.15,
        layer="below",
        line_width=0,
        row=2,
        col=1,
    )

fig.update_layout(
    title=dict(
        text="Signal Comparison",
        font=dict(color="black")
    ),
    height=700,
    dragmode="zoom",
    plot_bgcolor="white",
    paper_bgcolor="white",
    xaxis=dict(
        fixedrange=False,
        type="linear",
        title=dict(text="Sample index", font=dict(color="black")),
        tickfont=dict(color="black")
    ),
    xaxis2=dict(
        fixedrange=False,
        rangeslider=dict(visible=True),
        type="linear",
        title=dict(text="Sample index", font=dict(color="black")),
        tickfont=dict(color="black")
    ),
    yaxis=dict(
        title=dict(
            text=signal_a["metric"]["unit"],
            font=dict(color="black")
        ),
        fixedrange=True,
        tickfont=dict(color="black")
    ),
    yaxis2=dict(
        title=dict(
            text=signal_b["metric"]["unit"],
            font=dict(color="black")
        ),
        fixedrange=True,
        tickfont=dict(color="black")
    ),
    hovermode="x unified",
    legend=dict(
        orientation="h",
        yanchor="top",
        y=-0.15,
        xanchor="center",
        x=0.5,
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="black",
        borderwidth=1,
        font=dict(color="black")
    ),
    showlegend=True
)

for annotation in fig.layout.annotations:
    annotation.font.color = "black"

comparison_filename = f"{device_a}_{metric_a}_vs_{device_b}_{metric_b}".replace("::", "_").replace(" ", "_")
config = {
    "toImageButtonOptions": {
        "format": "png",
        "filename": comparison_filename,
        "height": 500,
        "width": 1000,
        "scale": 2,
    },
    "displaylogo": False,
}

st.plotly_chart(fig, use_container_width=True, config=config)
