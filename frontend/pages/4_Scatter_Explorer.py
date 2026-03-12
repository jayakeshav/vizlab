import colorsys

import numpy as np
import plotly.graph_objects as go
import requests
import streamlit as st


API_BASE = "http://127.0.0.1:8000"
FAMILY_ORDER = ["benign", "ba", "br", "r", "noflag", "other"]


st.set_page_config(
    page_title="VizLab - Scatter Explorer",
    layout="wide",
)

st.title("Scatter Explorer")
st.caption(
    "Build two ratios and overlay scatter plots from multiple files in the same device/workload."
)


def api_get(path, params=None):
    """Fetch data from the backend API."""
    try:
        response = requests.get(f"{API_BASE}{path}", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        st.error(f"API error: {exc}")
        st.stop()


def fetch_signal(device, workload, run, metric, window_size=1):
    """Fetch a single signal from the backend API."""
    return api_get(
        "/signal",
        {
            "device": device,
            "workload": workload,
            "run": run,
            "metric": metric,
            "window_size": window_size,
        },
    )


def classify_run_family(run_name):
    """Classify a run into a coarse family based on its filename."""
    normalized = run_name.lower()

    if "benign" in normalized:
        return "benign"
    if "_ba_" in normalized:
        return "ba"
    if "_br_" in normalized:
        return "br"
    if normalized.endswith("_noflag") or "noflag" in normalized:
        return "noflag"
    if "_r_" in normalized:
        return "r"
    return "other"


def family_sort_key(run_name):
    """Sort runs by family first, then by name."""
    family = classify_run_family(run_name)
    family_index = FAMILY_ORDER.index(family) if family in FAMILY_ORDER else len(FAMILY_ORDER)
    return (family_index, run_name.lower())


def build_ratio_for_run(device, workload, run, numerator_metric, denominator_metric):
    """Build one ratio series for a single run with session-scoped caching."""
    if numerator_metric == denominator_metric:
        raise ValueError("Numerator and denominator must be different metrics")

    cache_key = (device, workload, run, numerator_metric, denominator_metric)
    cache = st.session_state.scatter_ratio_cache
    if cache_key in cache:
        return cache[cache_key]

    numerator_signal = fetch_signal(device, workload, run, numerator_metric)
    denominator_signal = fetch_signal(device, workload, run, denominator_metric)

    numerator_values = np.array(numerator_signal["values"], dtype=float)
    denominator_values = np.array(denominator_signal["values"], dtype=float)

    with np.errstate(divide="ignore", invalid="ignore"):
        ratio_values = np.divide(numerator_values, denominator_values)
        ratio_values = np.where(np.isfinite(ratio_values), ratio_values, np.nan)

    numerator_labels = np.array(numerator_signal["labels"]["values"], dtype=int)
    denominator_labels = np.array(denominator_signal["labels"]["values"], dtype=int)
    combined_labels = np.logical_or(numerator_labels, denominator_labels).astype(int)

    min_len = min(
        len(numerator_signal["time"]["values"]),
        len(ratio_values),
        len(combined_labels),
    )

    ratio_data = {
        "name": f"{numerator_metric} / {denominator_metric}",
        "x": numerator_signal["time"]["values"][:min_len],
        "y": ratio_values[:min_len].tolist(),
        "labels": combined_labels[:min_len].tolist(),
    }
    cache[cache_key] = ratio_data
    return ratio_data


def generate_run_colors(index, total):
    """Generate per-run shades while preserving blue=idle and red=attack semantics."""
    if total <= 1:
        position = 0.5
    else:
        position = index / (total - 1)

    # Keep idle colors in the blue family and attack colors in the red family.
    blue_hue = (205 + 28 * position) / 360.0
    red_hue = (355 + 18 * position) / 360.0

    idle_rgb = colorsys.hls_to_rgb(blue_hue, 0.46, 0.72)
    attack_rgb = colorsys.hls_to_rgb(red_hue, 0.54, 0.82)

    idle_color = "rgb({},{},{})".format(
        int(idle_rgb[0] * 255),
        int(idle_rgb[1] * 255),
        int(idle_rgb[2] * 255),
    )
    attack_color = "rgb({},{},{})".format(
        int(attack_rgb[0] * 255),
        int(attack_rgb[1] * 255),
        int(attack_rgb[2] * 255),
    )

    return idle_color, attack_color


def render_selection_controls(runs, family_filter):
    """Render run include checkboxes and selection helpers."""
    if not runs:
        st.info("No files available for the selected device and workload.")
        return []

    filtered_runs = [
        run for run in sorted(runs, key=family_sort_key)
        if family_filter == "all" or classify_run_family(run) == family_filter
    ]

    if not filtered_runs:
        st.info("No files match the selected family filter.")
        return []

    action_col_1, action_col_2 = st.columns([1, 1])
    with action_col_1:
        if st.button("Select all visible files", use_container_width=True):
            for run in filtered_runs:
                st.session_state[f"include_run_{run}"] = True
            st.rerun()
    with action_col_2:
        if st.button("Clear visible files", use_container_width=True):
            for run in filtered_runs:
                st.session_state[f"include_run_{run}"] = False
            st.rerun()

    selected_runs = []
    with st.container(border=True):
        for run in filtered_runs:
            family = classify_run_family(run)
            checked = st.checkbox(
                f"{run} [{family}]",
                key=f"include_run_{run}",
            )
            if checked:
                selected_runs.append(run)

    return selected_runs


if "scatter_ratio_cache" not in st.session_state:
    st.session_state.scatter_ratio_cache = {}


devices = api_get("/devices")

scope_col_1, scope_col_2 = st.columns([1, 1])
with scope_col_1:
    selected_device = st.selectbox("Device", devices, key="scatter_device") if devices else None
with scope_col_2:
    workloads = api_get("/workloads", {"device": selected_device}) if selected_device else []
    selected_workload = (
        st.selectbox("Workload", workloads, key="scatter_workload") if workloads else None
    )

runs = (
    api_get("/runs", {"device": selected_device, "workload": selected_workload})
    if selected_device and selected_workload
    else []
)
metrics = api_get("/metrics", {"device": selected_device}) if selected_device else []

st.subheader("Files to Include")

family_options = ["all"] + [family for family in FAMILY_ORDER if family != "other"] + ["other"]
selected_family = st.selectbox(
    "Family filter",
    family_options,
    format_func=lambda family: family.upper() if family != "all" else "All families",
    key="scatter_family_filter",
)

selected_runs = render_selection_controls(runs, selected_family)

st.subheader("Scatter Axes")

axis_col_1, axis_col_2 = st.columns(2)

with axis_col_1:
    st.markdown("**X-axis ratio**")
    x_numerator = st.selectbox("X numerator", metrics, key="scatter_x_numerator") if metrics else None
    x_denominator = (
        st.selectbox("X denominator", metrics, key="scatter_x_denominator") if metrics else None
    )

with axis_col_2:
    st.markdown("**Y-axis ratio**")
    y_numerator = st.selectbox("Y numerator", metrics, key="scatter_y_numerator") if metrics else None
    y_denominator = (
        st.selectbox("Y denominator", metrics, key="scatter_y_denominator") if metrics else None
    )

st.subheader("Display")

display_col_1, display_col_2, display_col_3 = st.columns([1, 1, 1])
with display_col_1:
    marker_size = st.slider("Marker size", min_value=4, max_value=14, value=6)
with display_col_2:
    marker_opacity = st.slider("Opacity", min_value=0.2, max_value=1.0, value=0.65, step=0.05)
with display_col_3:
    point_filter = st.selectbox("Points to show", ["Both", "Idle only", "Attack only"])

render_clicked = st.button("Render scatter", type="primary")


if not render_clicked:
    st.info("Select files and define both ratios, then click Render scatter.")
    st.stop()

if not selected_device or not selected_workload:
    st.error("Device and workload are required.")
    st.stop()

if not selected_runs:
    st.error("Select at least one file to include.")
    st.stop()

if not all([x_numerator, x_denominator, y_numerator, y_denominator]):
    st.error("All ratio metric selections are required.")
    st.stop()

if x_numerator == x_denominator:
    st.error("X-axis numerator and denominator must be different metrics.")
    st.stop()

if y_numerator == y_denominator:
    st.error("Y-axis numerator and denominator must be different metrics.")
    st.stop()

figure = go.Figure()
total_valid_points = 0
total_idle_points = 0
total_attack_points = 0
selected_runs_sorted = sorted(selected_runs, key=family_sort_key)

for index, run in enumerate(selected_runs_sorted):
    x_ratio = build_ratio_for_run(
        selected_device,
        selected_workload,
        run,
        x_numerator,
        x_denominator,
    )
    y_ratio = build_ratio_for_run(
        selected_device,
        selected_workload,
        run,
        y_numerator,
        y_denominator,
    )

    min_len = min(len(x_ratio["y"]), len(y_ratio["y"]), len(x_ratio["labels"]), len(y_ratio["labels"]))

    x_values = np.array(x_ratio["y"][:min_len], dtype=float)
    y_values = np.array(y_ratio["y"][:min_len], dtype=float)
    labels = np.logical_or(
        np.array(x_ratio["labels"][:min_len], dtype=int),
        np.array(y_ratio["labels"][:min_len], dtype=int),
    ).astype(int)

    valid_mask = np.isfinite(x_values) & np.isfinite(y_values)
    x_clean = x_values[valid_mask]
    y_clean = y_values[valid_mask]
    labels_clean = labels[valid_mask]

    idle_mask = labels_clean == 0
    attack_mask = labels_clean == 1

    idle_color, attack_color = generate_run_colors(index, len(selected_runs_sorted))

    total_valid_points += int(valid_mask.sum())
    total_idle_points += int(idle_mask.sum())
    total_attack_points += int(attack_mask.sum())

    if point_filter in ["Both", "Idle only"] and idle_mask.any():
        figure.add_trace(
            go.Scatter(
                x=x_clean[idle_mask],
                y=y_clean[idle_mask],
                mode="markers",
                name=f"{run} • idle",
                marker=dict(size=marker_size, color=idle_color, opacity=marker_opacity),
                hovertemplate=(
                    f"Run: {run}<br>State: idle<br>X: %{{x}}<br>Y: %{{y}}<extra></extra>"
                ),
            )
        )

    if point_filter in ["Both", "Attack only"] and attack_mask.any():
        figure.add_trace(
            go.Scatter(
                x=x_clean[attack_mask],
                y=y_clean[attack_mask],
                mode="markers",
                name=f"{run} • attack",
                marker=dict(size=marker_size, color=attack_color, opacity=marker_opacity),
                hovertemplate=(
                    f"Run: {run}<br>State: attack<br>X: %{{x}}<br>Y: %{{y}}<extra></extra>"
                ),
            )
        )

summary_col_1, summary_col_2, summary_col_3, summary_col_4 = st.columns(4)
summary_col_1.metric("Files included", len(selected_runs_sorted))
summary_col_2.metric("Valid points", total_valid_points)
summary_col_3.metric("Idle points", total_idle_points)
summary_col_4.metric("Attack points", total_attack_points)

figure.update_layout(
    title=dict(
        text=(
            f"{selected_device} | {selected_workload} | "
            f"{x_numerator} / {x_denominator} vs {y_numerator} / {y_denominator}"
        ),
        font=dict(color="black"),
    ),
    xaxis_title=f"{x_numerator} / {x_denominator}",
    yaxis_title=f"{y_numerator} / {y_denominator}",
    height=700,
    plot_bgcolor="white",
    paper_bgcolor="white",
    hovermode="closest",
    legend=dict(
        bgcolor="rgba(255, 255, 255, 0.85)",
        bordercolor="black",
        borderwidth=1,
        font=dict(color="black"),
    ),
    xaxis=dict(
        tickfont=dict(color="black"),
        title=dict(font=dict(color="black")),
        zeroline=True,
        zerolinecolor="rgba(0, 0, 0, 0.15)",
        gridcolor="rgba(0, 0, 0, 0.08)",
    ),
    yaxis=dict(
        tickfont=dict(color="black"),
        title=dict(font=dict(color="black")),
        zeroline=True,
        zerolinecolor="rgba(0, 0, 0, 0.15)",
        gridcolor="rgba(0, 0, 0, 0.08)",
    ),
)

st.plotly_chart(figure, use_container_width=True)