import streamlit as st

st.set_page_config(
    page_title="VizLab",
    layout="wide"
)

st.title("VizLab - Performance Signal Explorer")

st.markdown("""
## Welcome to VizLab v2

VizLab is a research visualization tool for hardware performance counter time-series data with advanced signal analysis and ratio computation capabilities.

### Available Tools

1. **Single Signal Explorer** — Load and visualize a single performance signal with automatic attack region detection
2. **Compare Signals** — Compare two signals side-by-side with independent selection and dual-axis visualization
3. **Derived Ratios** — Compute and analyze derived metrics as ratios of two signals with batch plotting and scatter comparison

### Getting Started

Select a tool from the sidebar to get started. Each tool provides:
- Interactive signal exploration
- Attack region visualization (red shading)
- Zoom and range slider controls
- Export-ready Plotly charts

### Key Features

- **Multi-Signal Analysis** — Compare signals across different devices, workloads, and runs
- **Ratio Computation** — Derive new metrics from signal pairs with caching
- **Scatter Plots** — Compare ratios visually using scatter plots with idle/attack differentiation
- **Attack Detection** — Automatic red shading for attack regions
- **Performance-Optimized** — Caching prevents redundant computations

### Tips

- Use the sidebar to navigate between different analysis modes
- All signals are fetched from the backend API at `http://127.0.0.1:8000`
- Attack labels are computed from device configuration files
- Ratio cache is session-scoped and resets on page reload

---

**Version**: v2.0 | **Last Updated**: February 2026
""")
