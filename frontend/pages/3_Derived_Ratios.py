import streamlit as st
import requests
import plotly.graph_objects as go
import numpy as np

# -----------------------
# Config
# -----------------------
API_BASE = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="VizLab - Derived Ratios",
    layout="wide"
)

st.title("Derived Ratios")

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


devices = api_get("/devices")


# -----------------------
# Helper function to build ratio
# -----------------------
def build_ratio_data(entry_id, device_sel, workload_sel, run_sel, numerator_m, denominator_m):
    """Fetch and build a ratio entry."""
    if not device_sel or not workload_sel or not run_sel:
        st.error("Device, workload, and run are required for each ratio")
        return None

    if numerator_m == denominator_m:
        st.error("Numerator and denominator must be different metrics")
        return None

    cache_key = (device_sel, workload_sel, run_sel, numerator_m, denominator_m)

    try:
        if cache_key in st.session_state.ratio_cache:
            cached = st.session_state.ratio_cache[cache_key]
            return {
                "entry_id": entry_id,
                "name": cached["name"],
                "display_name": (
                    f"{device_sel} | {workload_sel} | {run_sel} | "
                    f"{numerator_m} / {denominator_m}"
                ),
                "x": cached["x"],
                "y": cached["y"],
                "labels": cached["labels"],
                "device": device_sel,
                "workload": workload_sel,
                "run": run_sel,
                "numerator": numerator_m,
                "denominator": denominator_m,
            }

        numerator_signal = fetch_signal(
            device_sel,
            workload_sel,
            run_sel,
            numerator_m
        )
        denominator_signal = fetch_signal(
            device_sel,
            workload_sel,
            run_sel,
            denominator_m
        )

        num_values = np.array(numerator_signal["values"])
        den_values = np.array(denominator_signal["values"])

        with np.errstate(divide='ignore', invalid='ignore'):
            ratio_values = np.divide(num_values, den_values)
            ratio_values = np.where(
                np.isfinite(ratio_values),
                ratio_values,
                np.nan
            )

        num_labels = np.array(numerator_signal["labels"]["values"])
        den_labels = np.array(denominator_signal["labels"]["values"])
        combined_labels = np.logical_or(num_labels, den_labels).astype(int).tolist()

        cached_ratio = {
            "name": f"{numerator_m} / {denominator_m}",
            "display_name": (
                f"{device_sel} | {workload_sel} | {run_sel} | "
                f"{numerator_m} / {denominator_m}"
            ),
            "x": numerator_signal["time"]["values"],
            "y": ratio_values.tolist(),
            "labels": combined_labels,
            "device": device_sel,
            "workload": workload_sel,
            "run": run_sel,
            "numerator": numerator_m,
            "denominator": denominator_m,
        }

        st.session_state.ratio_cache[cache_key] = cached_ratio

        return {
            "entry_id": entry_id,
            "name": cached_ratio["name"],
            "display_name": (
                f"{device_sel} | {workload_sel} | {run_sel} | "
                f"{numerator_m} / {denominator_m}"
            ),
            "x": cached_ratio["x"],
            "y": cached_ratio["y"],
            "labels": cached_ratio["labels"],
            "device": device_sel,
            "workload": workload_sel,
            "run": run_sel,
            "numerator": numerator_m,
            "denominator": denominator_m,
        }
    except Exception as e:
        st.error(f"Error: {e}")
        return None


# -----------------------
# Initialize Session State
# -----------------------
if "ratios" not in st.session_state:
    st.session_state.ratios = {}  # Dict keyed by entry_id

if "ratio_entry_counter" not in st.session_state:
    st.session_state.ratio_entry_counter = 0

if "ratio_cache" not in st.session_state:
    st.session_state.ratio_cache = {}

if "ratio_search_entries" not in st.session_state:
    st.session_state.ratio_search_entries = [
        {
            "id": 0,
            "device": None,
            "workload": None,
            "run": None,
            "numerator": None,
            "denominator": None,
        }
    ]
    st.session_state.ratio_entry_counter = 1
else:
    # Migrate old entries to have IDs if they don't
    max_id = -1
    for entry in st.session_state.ratio_search_entries:
        if "id" not in entry:
            if "id" not in entry:
                max_id += 1
                entry["id"] = max_id
        else:
            max_id = max(max_id, entry["id"])
    
    if "ratio_entry_counter" not in st.session_state:
        st.session_state.ratio_entry_counter = max_id + 1


# -----------------------
# Ratio Selection (Main Page)
# -----------------------
st.subheader("Build Ratios")

for ratio_idx, entry in enumerate(st.session_state.ratio_search_entries):
    # Ensure entry has an id
    if "id" not in entry:
        entry["id"] = st.session_state.ratio_entry_counter
        st.session_state.ratio_entry_counter += 1
    
    st.markdown(f"**Ratio {ratio_idx + 1}**")

    col1, col2, col3 = st.columns(3)
    with col1:
        device_sel = st.selectbox(
            "Device",
            devices,
            index=devices.index(entry["device"]) if entry["device"] in devices else 0,
            key=f"device_sel_{ratio_idx}"
        ) if devices else None

    with col2:
        workloads = api_get("/workloads", {"device": device_sel}) if device_sel else []
        workload_sel = st.selectbox(
            "Workload",
            workloads,
            index=workloads.index(entry["workload"]) if entry["workload"] in workloads else 0,
            key=f"workload_sel_{ratio_idx}"
        ) if workloads else None

    with col3:
        runs = api_get(
            "/runs",
            {"device": device_sel, "workload": workload_sel}
        ) if device_sel and workload_sel else []
        run_sel = st.selectbox(
            "Run",
            runs,
            index=runs.index(entry["run"]) if entry["run"] in runs else 0,
            key=f"run_sel_{ratio_idx}"
        ) if runs else None

    metrics = api_get("/metrics", {"device": device_sel}) if device_sel else []

    col4, col5, col6 = st.columns([1, 1, 1])
    with col4:
        numerator_m = st.selectbox(
            "Numerator metric",
            metrics,
            index=metrics.index(entry["numerator"]) if entry["numerator"] in metrics else 0,
            key=f"numerator_metric_{ratio_idx}"
        ) if metrics else None

    with col5:
        denominator_m = st.selectbox(
            "Denominator metric",
            metrics,
            index=metrics.index(entry["denominator"]) if entry["denominator"] in metrics else 0,
            key=f"denominator_metric_{ratio_idx}"
        ) if metrics else None

    with col6:
        st.write("")
        st.write("")
        if st.button("Plot this ratio", key=f"plot_ratio_btn_{ratio_idx}"):
            ratio_data = build_ratio_data(
                entry["id"],
                device_sel,
                workload_sel,
                run_sel,
                numerator_m,
                denominator_m
            )
            if ratio_data:
                st.session_state.ratios[entry["id"]] = ratio_data
                st.rerun()

    col7, col8, col9 = st.columns([1, 1, 1])
    with col7:
        if st.button("Duplicate search", key=f"duplicate_search_btn_{ratio_idx}"):
            new_id = st.session_state.ratio_entry_counter
            st.session_state.ratio_entry_counter += 1
            st.session_state.ratio_search_entries.append(
                {
                    "id": new_id,
                    "device": device_sel,
                    "workload": workload_sel,
                    "run": run_sel,
                    "numerator": numerator_m,
                    "denominator": denominator_m,
                }
            )
            st.rerun()

    with col8:
        if st.button("Delete search", key=f"delete_search_btn_{ratio_idx}"):
            if len(st.session_state.ratio_search_entries) > 1:
                entry_id = entry["id"]
                st.session_state.ratio_search_entries.pop(ratio_idx)
                if entry_id in st.session_state.ratios:
                    del st.session_state.ratios[entry_id]
            else:
                st.session_state.ratio_search_entries[0] = {
                    "id": st.session_state.ratio_search_entries[0]["id"],
                    "device": None,
                    "workload": None,
                    "run": None,
                    "numerator": None,
                    "denominator": None,
                }
            st.rerun()

    with col9:
        st.write("")

    st.session_state.ratio_search_entries[ratio_idx] = {
        "id": entry["id"],
        "device": device_sel,
        "workload": workload_sel,
        "run": run_sel,
        "numerator": numerator_m,
        "denominator": denominator_m,
    }

    st.divider()

if st.button("+ Add another ratio input", key="add_ratio_input_btn"):
    new_id = st.session_state.ratio_entry_counter
    st.session_state.ratio_entry_counter += 1
    st.session_state.ratio_search_entries.append(
        {
            "id": new_id,
            "device": None,
            "workload": None,
            "run": None,
            "numerator": None,
            "denominator": None,
        }
    )
    st.rerun()

st.divider()

# "Plot ALL ratios" button
if st.button("Plot ALL ratios", key="plot_all_ratios_btn"):
    new_ratios = {}
    for entry in st.session_state.ratio_search_entries:
        # Ensure entry has an id
        if "id" not in entry:
            entry["id"] = st.session_state.ratio_entry_counter
            st.session_state.ratio_entry_counter += 1
        
        entry_id = entry["id"]
        device_sel = entry["device"]
        workload_sel = entry["workload"]
        run_sel = entry["run"]
        numerator_m = entry["numerator"]
        denominator_m = entry["denominator"]
        
        if device_sel and workload_sel and run_sel and numerator_m and denominator_m:
            ratio_data = build_ratio_data(entry_id, device_sel, workload_sel, run_sel, numerator_m, denominator_m)
            if ratio_data:
                new_ratios[entry_id] = ratio_data
    
    st.session_state.ratios = new_ratios
    st.rerun()


# -----------------------
# Display Stored Ratios
# -----------------------
if st.session_state.ratios:
    st.subheader("Plotted Ratios")

    # Render plots in the order of ratio_search_entries
    for entry in st.session_state.ratio_search_entries:
        # Ensure entry has an id
        if "id" not in entry:
            entry["id"] = st.session_state.ratio_entry_counter
            st.session_state.ratio_entry_counter += 1
        
        entry_id = entry["id"]
        if entry_id not in st.session_state.ratios:
            continue
        
        ratio = st.session_state.ratios[entry_id]
        st.markdown(f"**{ratio['display_name']}**")
        
        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=ratio["x"],
                y=ratio["y"],
                mode="lines",
                name=ratio["name"],
                line=dict(width=2, color="blue"),
            )
        )

        # Attack shading using labels
        labels = ratio["labels"]
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
            xaxis_title="Sample index",
            yaxis_title="Ratio value",
            height=350,
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
                tickfont=dict(color="black"),
                title=dict(font=dict(color="black"))
            ),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="top",
                y=-0.2,
                xanchor="center",
                x=0.5,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="black",
                borderwidth=1,
                font=dict(color="black")
            ),
            showlegend=True,
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
            key=f"ratio_timeseries_{entry_id}"
        )

    st.divider()

    # Clear button
    if st.button("Clear all plots"):
        st.session_state.ratios = {}
        st.rerun()

    st.divider()

    # Scatter comparison
    if len(st.session_state.ratios) >= 2:
        st.subheader("Pair Comparison (Scatter)")

        ratios_list = list(st.session_state.ratios.values())
        pair_labels = [f"Pair {i+1}: {ratios_list[i]['display_name']}" for i in range(len(ratios_list))]
        pair_entry_ids = [r["entry_id"] for r in ratios_list]

        col1, col2, col3 = st.columns([1, 1, 1])

        with col1:
            pair_x_label = st.selectbox(
                "X-axis pair",
                pair_labels,
                key="scatter_x_pair"
            )

        with col2:
            pair_y_label = st.selectbox(
                "Y-axis pair",
                pair_labels,
                key="scatter_y_pair"
            )

        with col3:
            st.write("")
            st.write("")
            render_scatter = st.button("Render scatter")

        if render_scatter and pair_x_label and pair_y_label:
            pair_x_idx = pair_labels.index(pair_x_label)
            pair_y_idx = pair_labels.index(pair_y_label)

            x_ratio = ratios_list[pair_x_idx]
            y_ratio = ratios_list[pair_y_idx]
            
            x_vals = x_ratio["y"]
            y_vals = y_ratio["y"]
            x_labels = x_ratio["labels"]
            y_labels = y_ratio["labels"]

            valid_idx = [
                i for i, (x, y) in enumerate(zip(x_vals, y_vals))
                if np.isfinite(x) and np.isfinite(y)
            ]
            x_clean = [x_vals[i] for i in valid_idx]
            y_clean = [y_vals[i] for i in valid_idx]
            labels_clean = [
                max(x_labels[i], y_labels[i]) for i in valid_idx
            ]

            idle_x = [x_clean[i] for i, l in enumerate(labels_clean) if l == 0]
            idle_y = [y_clean[i] for i, l in enumerate(labels_clean) if l == 0]
            attack_x = [x_clean[i] for i, l in enumerate(labels_clean) if l == 1]
            attack_y = [y_clean[i] for i, l in enumerate(labels_clean) if l == 1]

            fig_scatter = go.Figure()

            fig_scatter.add_trace(
                go.Scatter(
                    x=idle_x,
                    y=idle_y,
                    mode="markers",
                    name="Idle",
                    marker=dict(size=5, color="blue", opacity=0.6),
                )
            )

            fig_scatter.add_trace(
                go.Scatter(
                    x=attack_x,
                    y=attack_y,
                    mode="markers",
                    name="Attack",
                    marker=dict(size=5, color="red", opacity=0.6),
                )
            )

            fig_scatter.update_layout(
                title=dict(
                    text=f"{x_ratio['name']} vs {y_ratio['name']}",
                    font=dict(color="black")
                ),
                xaxis_title=x_ratio['name'],
                yaxis_title=y_ratio['name'],
                height=500,
                plot_bgcolor="white",
                paper_bgcolor="white",
                xaxis=dict(
                    tickfont=dict(color="black"),
                    title=dict(font=dict(color="black")),
                ),
                yaxis=dict(
                    tickfont=dict(color="black"),
                    title=dict(font=dict(color="black")),
                ),
                hovermode="closest",
                legend=dict(
                    bgcolor="rgba(255, 255, 255, 0.8)",
                    bordercolor="black",
                    borderwidth=1,
                    font=dict(color="black"),
                ),
            )

            st.plotly_chart(
                fig_scatter,
                use_container_width=True,
                key=f"scatter_{pair_entry_ids[pair_x_idx]}_{pair_entry_ids[pair_y_idx]}"
            )

else:
    st.info("Add ratios using the controls above to start plotting and comparing.")
