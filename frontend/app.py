import streamlit as st
import requests
import plotly.graph_objects as go

# -----------------------
# Config
# -----------------------
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="VizLab",
    layout="wide"
)

st.title("VizLab — Performance Signal Explorer (v1)")

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
# Sidebar Functions
# -----------------------
def render_sidebar():
    """Render sidebar controls for single signal mode and return Load button state."""
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
    return load_clicked


def render_sidebar_a():
    """Render controls for Signal A in comparison mode and return Load button state."""
    col1, col2 = st.columns([4, 1])
    with col1:
        devices = api_get("/devices")
        st.selectbox(
            "Device",
            devices,
            key="device_a"
        )

    workloads = api_get("/workloads", {"device": st.session_state.device_a})
    st.selectbox(
        "Workload",
        workloads,
        key="workload_a"
    )

    runs = api_get(
        "/runs",
        {
            "device": st.session_state.device_a,
            "workload": st.session_state.workload_a,
        }
    )
    st.selectbox(
        "Run",
        runs,
        key="run_a"
    )

    metrics = api_get("/metrics", {"device": st.session_state.device_a})
    st.selectbox(
        "Metric",
        metrics,
        key="metric_a"
    )


def render_sidebar_b():
    """Render controls for Signal B in comparison mode and return Load button state."""
    col1, col2 = st.columns([4, 1])
    with col1:
        devices = api_get("/devices")
        st.selectbox(
            "Device",
            devices,
            key="device_b"
        )

    workloads = api_get("/workloads", {"device": st.session_state.device_b})
    st.selectbox(
        "Workload",
        workloads,
        key="workload_b"
    )

    runs = api_get(
        "/runs",
        {
            "device": st.session_state.device_b,
            "workload": st.session_state.workload_b,
        }
    )
    st.selectbox(
        "Run",
        runs,
        key="run_b"
    )

    metrics = api_get("/metrics", {"device": st.session_state.device_b})
    st.selectbox(
        "Metric",
        metrics,
        key="metric_b"
    )


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
            line=dict(width=2),
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
        title=signal["signal_id"],
        xaxis_title="Sample index",
        yaxis_title=signal["metric"]["unit"],
        height=500,
        dragmode="zoom",
        xaxis=dict(
            fixedrange=False,
            rangeslider=dict(visible=True),
            type="linear",
        ),
        yaxis=dict(
            fixedrange=True
        )
    )

    st.plotly_chart(fig, use_container_width=True)


def render_signal_plot_comparison(signal_a, signal_b):
    """Render comparison plot with two signals and their respective attack regions."""
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
    
    fig = go.Figure()
    
    # Signal A trace
    device_a = signal_a["source"]["device"]
    metric_a = signal_a["metric"]["name"]
    fig.add_trace(
        go.Scatter(
            x=x_a,
            y=y_a,
            mode="lines",
            name=f"{device_a}::{metric_a} (A)",
            line=dict(width=2, color="blue"),
            yaxis="y1",
        )
    )
    
    # Signal B trace
    device_b = signal_b["source"]["device"]
    metric_b = signal_b["metric"]["name"]
    fig.add_trace(
        go.Scatter(
            x=x_b,
            y=y_b,
            mode="lines",
            name=f"{device_b}::{metric_b} (B)",
            line=dict(width=2, color="green"),
            yaxis="y2",
        )
    )
    
    # Attack shading for Signal A (red)
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
        )
    
    # Attack shading for Signal B (orange)
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
        )
    
    fig.update_layout(
        title="Signal Comparison",
        xaxis_title="Sample index",
        height=500,
        dragmode="zoom",
        xaxis=dict(
            fixedrange=False,
            rangeslider=dict(visible=True),
            type="linear",
        ),
        yaxis=dict(
            title=signal_a["metric"]["unit"],
            fixedrange=True,
        ),
        yaxis2=dict(
            title=signal_b["metric"]["unit"],
            overlaying="y",
            side="right",
            fixedrange=True,
        ),
        hovermode="x unified",
    )
    
    st.plotly_chart(fig, use_container_width=True)


# -----------------------
# Main
# -----------------------
def main():
    """Main application flow."""
    # Comparison mode toggle
    col1, col2 = st.columns([0.3, 0.7])
    with col1:
        comparison_mode = st.toggle("Comparison mode", value=False)
    
    if comparison_mode:
        # Two-column layout for signal A and signal B
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.subheader("Signal A")
            load_a = render_sidebar_a()
        
        with col_b:
            st.subheader("Signal B")
            load_b = render_sidebar_b()
        
        load_clicked = st.button("Load signals")
        
        if load_clicked:
            signal_a = fetch_signal(
                st.session_state.device_a,
                st.session_state.workload_a,
                st.session_state.run_a,
                st.session_state.metric_a,
                window_size=1,
            )
            signal_b = fetch_signal(
                st.session_state.device_b,
                st.session_state.workload_b,
                st.session_state.run_b,
                st.session_state.metric_b,
                window_size=1,
            )
            st.session_state.signal_a = signal_a
            st.session_state.signal_b = signal_b
        
        if "signal_a" not in st.session_state or "signal_b" not in st.session_state:
            st.info("Select parameters for both signals and click **Load signals**")
            st.stop()
        
        render_signal_plot_comparison(
            st.session_state.signal_a,
            st.session_state.signal_b
        )
    
    else:
        # Single signal mode
        load_clicked = render_sidebar()

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


if __name__ == "__main__":
    main()