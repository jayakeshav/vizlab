import streamlit as st
import requests
import plotly.graph_objects as go

# -----------------------
# Config
# -----------------------
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="VizLab - Single Signal",
    layout="wide"
)

st.title("Single Signal Explorer")

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


def api_post(path):
    """POST request to backend API."""
    try:
        r = requests.post(f"{API_BASE}{path}")
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
# Plot Functions
# -----------------------
def render_signal_plot(signal, metric_name):
    """Render time-series plot with attack regions shaded."""
    x = signal["time"]["values"]
    y = signal["values"]
    labels = signal["labels"]["values"]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=x,
            y=y,
            mode="lines",
            name=metric_name,
            line=dict(width=2,color="blue"),
        )
    )

    # Attack shading — per contiguous segment
    in_attack = False
    start = None

    for i, v in enumerate(labels):
        if v == 1 and not in_attack:
            start = i
            in_attack = True
        elif v == 0 and in_attack:
            fig.add_vrect(
                x0=start,
                x1=i,
                fillcolor="red",
                opacity=0.15,
                layer="below",
                line_width=0,
            )
            in_attack = False

    if in_attack:
        fig.add_vrect(
            x0=start,
            x1=len(labels),
            fillcolor="red",
            opacity=0.15,
            layer="below",
            line_width=0,
        )

    fig.update_layout(
        title=dict(
            text=signal["signal_id"],
            font=dict(color="black")
        ),
        xaxis_title="Sample index",
        yaxis_title=signal["metric"]["unit"],
        height=500,
        dragmode="zoom",
        plot_bgcolor="white",
        paper_bgcolor="white",
        xaxis=dict(
            fixedrange=False,
            rangeslider=dict(visible=True),
            type="linear",
            title=dict(font=dict(color="black")),
            tickfont=dict(color="black")
        ),
        yaxis=dict(
            fixedrange=True,
            title=dict(font=dict(color="black")),
            tickfont=dict(color="black")
        ),
        legend=dict(
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="black",
            borderwidth=1,
            font=dict(color="black")
        )
    )

    plot_title = signal["signal_id"]
    sanitized_filename = plot_title.replace("::", "_")
    config = {
        "toImageButtonOptions": {
            "format": "png",
            "filename": sanitized_filename,
            "height": 500,
            "width": 1000,
            "scale": 2,
        },
        "displaylogo": False,
    }

    st.plotly_chart(fig, use_container_width=True, config=config)


# -----------------------
# Sidebar Controls
# -----------------------
st.sidebar.header("Selection")

col1, col2 = st.sidebar.columns([4, 1])
with col2:
    if st.button("🔄", help="Reload backend registry"):
        api_post("/reload")
        st.rerun()

devices = api_get("/devices")
st.sidebar.selectbox(
    "Device",
    devices,
    key="device"
)

workloads = api_get("/workloads", {"device": st.session_state.device})
st.sidebar.selectbox(
    "Workload",
    workloads,
    key="workload"
)

runs = api_get(
    "/runs",
    {
        "device": st.session_state.device,
        "workload": st.session_state.workload,
    }
)
st.sidebar.selectbox(
    "Run",
    runs,
    key="run"
)

metrics = api_get("/metrics", {"device": st.session_state.device})
st.sidebar.selectbox(
    "Metric",
    metrics,
    key="metric"
)

load_clicked = st.sidebar.button("Load signal")

# -----------------------
# Main Logic
# -----------------------
if load_clicked:
    signal = fetch_signal(
        st.session_state.device,
        st.session_state.workload,
        st.session_state.run,
        st.session_state.metric,
        window_size=1,
    )
    st.session_state.signal = signal

if "signal" not in st.session_state:
    st.info("Select parameters and click **Load signal**")
    st.stop()

render_signal_plot(st.session_state.signal, st.session_state.metric)
