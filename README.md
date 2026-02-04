# VizLab — Performance Signal Explorer

A research visualization tool for hardware performance counter time-series data. VizLab combines a FastAPI backend with a Streamlit frontend to enable interactive exploration and comparison of system performance signals.

## Architecture

- **Backend**: FastAPI (Python) — Loads device configs, manages signal fetching from CSV files
- **Frontend**: Streamlit (Python) — Interactive UI for signal selection, visualization, and comparison

## Project Structure

```
vizlab/
├── backend/
│   ├── app.py              # FastAPI application
│   ├── requirements.txt    # Backend dependencies
│   └── app.ipynb           # Jupyter notebook for development
└── frontend/
    ├── app.py              # Streamlit application
    └── requirements.txt    # Frontend dependencies
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

### Reload Registry

Click the 🔄 button in the sidebar to reload the backend device registry without restarting the server.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/devices` | GET | List all available devices |
| `/workloads` | GET | List workloads for a device |
| `/runs` | GET | List runs for a device + workload |
| `/metrics` | GET | List metrics for a device |
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

## Development

### Backend Changes

Edit `backend/app.py` and the server will auto-reload.

### Frontend Changes

Edit `frontend/app.py` and Streamlit will auto-detect changes.

### Device Configs

Add or modify `Master_Data_Sets/<device_name>/device_config.json` to define metrics and batches. Use the reload button to pick up changes without restarting.

## Notes

- All attack labels come from the backend — no inference in the frontend
- CSV files are read by the backend only
- Frontend consumes data exclusively through REST APIs
- Comparison mode truncates signals to minimum length for x-axis alignment
