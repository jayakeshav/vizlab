import streamlit as st

st.set_page_config(
    page_title="VizLab",
    layout="wide"
)

st.title("VizLab")

st.markdown("""
## Performance Signal Explorer

VizLab is a research visualization tool for hardware performance counter time-series data.

### Available Tools

- **Single Signal Explorer** — Load and visualize a single performance signal with automatic attack region detection
- **Compare Signals** — Compare two signals side-by-side with independent selection and dual-axis visualization

Select a tool from the sidebar to get started.
""")
