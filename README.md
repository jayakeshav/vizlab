# VizLab — Performance Signal Explorer

A research visualization tool for hardware performance counter time-series data. VizLab combines a FastAPI backend with a Streamlit frontend to enable interactive exploration, comparison, and ratio analysis of system performance signals.

## What's New in v2

- **Derived Ratios Page** — Compute and plot derived metrics as ratios of two signals
  - Per-ratio plotting: Select device/workload/run/metrics independently for each ratio
  - "Plot this ratio" button for individual computations
  - "Plot ALL ratios" button for batch processing
  - Ratio caching to avoid recomputation
  - Scatter plot comparison of any two plotted ratios
- **Metric Ordering** — Metrics now display in device_config order (default batch → batch1 → batch2) instead of alphabetically
- **Multi-Page UI** — Streamlit sidebar navigation with dedicated pages for each analysis mode

## Architecture

- **Backend**: FastAPI (Python) — Loads device configs, manages signal fetching from CSV files, computes ratio metrics
- **Frontend**: Streamlit (Python) — Interactive multi-page UI for signal selection, visualization, comparison, and ratio analysis

## Project Structure

```
vizlab/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Backend dependencies
│   └── app.ipynb           # Jupyter notebook for development
└── frontend/
    ├── app.py              # Streamlit main page
    ├── requirements.txt    # Frontend dependencies
    └── pages/
        ├── 1_Single_Signal.py      # Single signal explorer
        ├── 2_Compare_Signals.py    # Dual-signal comparison
        └── 3_Derived_Ratios.py     # Ratio builder & scatter analysis
```

Performance counter datasets are loaded from the configured data directory (typically `Master_Data_Sets/` containing device subdirectories with CSV files and device configs).

## Setup

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Running the Application

### Start the Backend

```bash
cd backend
source .venv/bin/activate
uvicorn app:app --reload
```

The API will be available at `http://127.0.0.1:8000`

API documentation: `http://127.0.0.1:8000/docs`

### Start the Frontend

```bash
cd frontend
source .venv/bin/activate
streamlit run app.py
```

The frontend will open in your browser at `http://localhost:8501`

## Features

### Single Signal Mode

- Select device, workload, run, and metric from sidebar
- Load and visualize a single signal
- Automatic detection and shading of attack regions (red overlay)
- Interactive Plotly chart with zoom and range slider controls

### Comparison Mode

Toggle "Comparison mode" at the top of the page to:

- Select two signals independently (Signal A and Signal B)
- Compare them on the same plot with dual y-axes
- Red shading indicates attacks in Signal A
- Orange shading indicates attacks in Signal B
- Automatic truncation to minimum signal length for alignment

### Derived Ratios Mode (v2)

Build and visualize derived metrics as ratios of two signals:

- **Build Ratios** — Add multiple ratio search entries with independent device/workload/run/metric selection
  - "Plot this ratio" button — Compute and plot individual ratios
  - "Duplicate search" button — Clone current entry settings
  - "Delete search" button — Remove an entry
- **Plotted Ratios** — View all computed ratios with attack region shading
- **Ratio Caching** — Prevents recomputation of identical ratios across plots
- **Pair Comparison** — Create scatter plots comparing any two plotted ratios
  - Filter by idle/attack labels
  - Dual-color visualization (blue = idle, red = attack)

Features:
- Per-ratio data source selection
- Automatic ratio caching to avoid recomputation
- Attack label merging (OR logic: attack if either numerator or denominator is attack)
- Divide-by-zero safety with NaN handling
- "Plot ALL ratios" for batch plotting

### Reload Registry

Click the 🔄 button in the sidebar to reload the backend device registry without restarting the server.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices` | GET | List all available devices |
| `/workloads` | GET | List workloads for a device |
| `/runs` | GET | List runs for a device + workload |
| `/metrics` | GET | List metrics for a device (ordered by device_config batches) |
| `/signal` | GET | Fetch a single signal with attack labels |
| `/reload` | POST | Reload backend device registry |

## Data Format

Each signal response includes:

```json
{
  "signal_id": "device::workload::run::metric",
  "source": {
    "device": "...",
    "workload": "...",
    "run": "..."
  },
  "metric": {
    "name": "...",
    "unit": "events"
  },
  "time": {
    "type": "index",
    "values": [...]
  },
  "values": [...],
  "labels": {
    "type": "attack",
    "values": [0, 1, 0, ...],
    "batch": "..."
  },
  "transform": {
    "window_size": 1,
    "aggregation": "none"
  }
}
```

**Labels**: `1` indicates attack region, `0` indicates benign. Labels are computed by the backend from device config.

## Derived Ratios Implementation Details

### Per-Ratio Plotting

Each ratio search entry is independently tracked:
- Device, workload, run, numerator metric, denominator metric
- Clicking "Plot this ratio" computes only that ratio
- Results stored in `st.session_state.ratios` dict (keyed by entry_id)
- Each entry can be re-plotted without affecting others

### Batch Plotting

"Plot ALL ratios" iterates through all entries and:
- Skips entries with missing selections
- Reuses cached ratios when possible
- Replaces entire ratios dict (overwrites previous plots)
- Triggers full re-render

### Ratio Computation

1. Fetch numerator signal from backend
2. Fetch denominator signal from backend
3. Divide arrays element-wise with divide-by-zero handling
4. Merge attack labels (OR logic: 1 if either signal has attack)
5. Cache result by (device, workload, run, numerator_metric, denominator_metric) key

### Scatter Comparison

- Select any two plotted ratios as X and Y axes
- Filters out non-finite values
- Renders idle (blue) and attack (red) points separately
- Hover info shows exact coordinates

## Development

### Backend Changes

Edit `backend/app.py` and the server will auto-reload.

### Frontend Changes

Edit pages in `frontend/pages/` and Streamlit will auto-detect changes.

### Adding New Pages

Create new files in `frontend/pages/` following Streamlit's naming convention:
- Files are automatically discovered
- Use sidebar for navigation (built-in)
- Import shared functions from main app

### Device Configs

Add or modify `Master_Data_Sets/<device_name>/device_config.json` to define metrics and batches. Use the reload button to pick up changes without restarting.

Device config structure:
```json
{
  "batches": {
    "default": {
      "probe_prefix": "...",
      "probes": [...],
      "metrics": [...]
    },
    "batch1": {...},
    "batch2": {...}
  }
}
```

Metrics appear in order: default batch → batch1 → batch2 (no alphabetical sorting).

## Notes

- All attack labels come from the backend — no inference in the frontend
- CSV files are read by the backend only
- Frontend consumes data exclusively through REST APIs
- Comparison mode truncates signals to minimum length for x-axis alignment
- Ratio computation is lazy — plots only created on button click
- Ratio cache is session-scoped and cleared on page reload

## Session State Management

The frontend uses Streamlit's session state to track:
- `ratios` — Dict of computed ratios keyed by entry_id
- `ratio_cache` — Dict of cached signal pairs to avoid re-fetching
- `ratio_search_entries` — List of ratio search entry configurations
- `ratio_entry_counter` — Counter for unique entry IDs

This ensures plots persist across widget interactions and sidebar changes.
