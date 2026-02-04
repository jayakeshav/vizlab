from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd
import numpy as np
import json
from pydantic import BaseModel
from typing import List, Dict, Any


app = FastAPI(title="VizLab API")


DATA_ROOT = Path("../Master_Data_Sets")

DEVICE_REGISTRY = {}

@app.on_event("startup")
def load_registry():
    global DEVICE_REGISTRY
    DEVICE_REGISTRY.clear()

    for device_dir in DATA_ROOT.iterdir():
        if not device_dir.is_dir():
            continue

        cfg_path = device_dir / "device_config.json"
        if not cfg_path.exists():
            continue  # skip malformed devices

        with open(cfg_path) as f:
            device_cfg = json.load(f)

        # metrics come ONLY from config
        metrics = []
        for batch in device_cfg["batches"].values():
            metrics.extend(batch["metrics"])

        workloads = {}
        for workload_dir in device_dir.iterdir():
            if not workload_dir.is_dir():
                continue
            if workload_dir.name == "__pycache__":
                continue

            runs = [
                f.stem
                for f in workload_dir.glob("*.csv")
                if f.name != "experiments_master_log.csv"
            ]

            workloads[workload_dir.name] = {
                "runs": sorted(runs)
            }

        DEVICE_REGISTRY[device_dir.name] = {
            "path": device_dir,
            "config": device_cfg,
            "metrics": sorted(set(metrics)),
            "workloads": workloads,
        }

    print(f"Loaded {len(DEVICE_REGISTRY)} devices")

class SignalSource(BaseModel):
    device: str
    workload: str
    run: str

class SignalMetric(BaseModel):
    name: str
    unit: str

class SignalTime(BaseModel):
    type: str
    values: List[int]

class SignalLabels(BaseModel):
    type: str
    values: List[int]
    batch: str

class SignalTransform(BaseModel):
    window_size: int
    aggregation: str

class Signal(BaseModel):
    signal_id: str
    source: SignalSource
    metric: SignalMetric
    time: SignalTime
    values: List[float]
    labels: SignalLabels
    transform: SignalTransform

class SignalRequest(BaseModel):
    device: str
    workload: str
    run: str
    metric: str
    window_size: int = 1

class SignalsRequest(BaseModel):
    requests: List[SignalRequest]

class SignalsResponse(BaseModel):
    signals: List[Signal]


@app.get("/")
def root():
    return {"status": "VizLab backend alive"}

@app.get("/devices")
def list_devices():
    return sorted(DEVICE_REGISTRY.keys())

@app.get("/metrics")
def list_metrics(device: str):
    if device not in DEVICE_REGISTRY:
        raise HTTPException(404, "Device not found")
    return DEVICE_REGISTRY[device]["metrics"]

@app.get("/workloads")
def list_workloads(device: str):
    if device not in DEVICE_REGISTRY:
        raise HTTPException(404, "Device not found")
    return sorted(DEVICE_REGISTRY[device]["workloads"].keys())

@app.get("/runs")
def list_runs(device: str, workload: str):
    if device not in DEVICE_REGISTRY:
        raise HTTPException(404, "Device not found")

    workloads = DEVICE_REGISTRY[device]["workloads"]
    if workload not in workloads:
        raise HTTPException(404, "Workload not found")

    return workloads[workload]["runs"]


def find_metric_batch(device_cfg, metric_name):
    for batch_name, batch in device_cfg["batches"].items():
        if metric_name in batch["metrics"]:
            return batch_name
    raise ValueError(f"Metric not defined in device config: {metric_name}")

def select_probe_columns(df, device_cfg, metric_name):
    batch_name = find_metric_batch(device_cfg, metric_name)
    batch = device_cfg["batches"][batch_name]

    prefix = batch["probe_prefix"]
    probe_names = batch["probes"]

    return [
        c for c in df.columns
        if c.startswith(prefix)
           and any(p in c for p in probe_names)
    ]

def derive_labels(df, device_cfg, metric_name):
    probe_cols = select_probe_columns(df, device_cfg, metric_name)

    if not probe_cols:
        return np.zeros(len(df), dtype=int)

    return (df[probe_cols] > 0).any(axis=1).astype(int).values

def make_signal(
    df,
    device_cfg,
    device,
    workload,
    run,
    metric,
    window_size=1,
):
    # Safety invariant (important!)
    cfg_device = device_cfg.get("device", {}).get("name")
    if cfg_device and cfg_device != device:
        raise RuntimeError(
            f"Device config mismatch: cfg={cfg_device}, request={device}"
        )

    labels = derive_labels(df, device_cfg, metric)

    return {
        "signal_id": f"{device}::{workload}::{run}::{metric}",
        "source": {
            "device": device,
            "workload": workload,
            "run": run,
        },
        "metric": {
            "name": metric,
            "unit": "events",
        },
        "time": {
            "type": "index",
            "values": df["index"].tolist(),
        },
        "values": df[metric].tolist(),
        "labels": {
            "type": "attack",
            "values": labels.tolist(),
            "batch": find_metric_batch(device_cfg, metric),
        },
        "transform": {
            "window_size": window_size,
            "aggregation": "none",
        },
    }

@app.get("/signal", response_model=Signal)
def get_signal(
    device: str,
    workload: str,
    run: str,
    metric: str,
    window_size: int = 1,
):
    # 1️⃣ Registry validation (single source of truth)
    if device not in DEVICE_REGISTRY:
        raise HTTPException(404, f"Device not found: {device}")

    entry = DEVICE_REGISTRY[device]

    if workload not in entry["workloads"]:
        raise HTTPException(404, f"Workload not found: {workload}")

    if run not in entry["workloads"][workload]["runs"]:
        raise HTTPException(404, f"Run not found: {run}")

    if metric not in entry["metrics"]:
        raise HTTPException(400, f"Metric not valid for device: {metric}")

    # 2️⃣ Load CSV ONCE
    csv_path = entry["path"] / workload / f"{run}.csv"
    df = pd.read_csv(csv_path)

    # 3️⃣ Core logic
    return make_signal(
        df=df,
        device_cfg=entry["config"],
        device=device,
        workload=workload,
        run=run,
        metric=metric,
        window_size=window_size,
    )


@app.post("/signals", response_model=SignalsResponse)
def get_signals(payload: SignalsRequest):
    results = []

    for req in payload.requests:
        # Registry validation
        if req.device not in DEVICE_REGISTRY:
            raise HTTPException(404, f"Device not found: {req.device}")

        entry = DEVICE_REGISTRY[req.device]

        if req.workload not in entry["workloads"]:
            raise HTTPException(404, f"Workload not found: {req.workload}")

        if req.run not in entry["workloads"][req.workload]["runs"]:
            raise HTTPException(404, f"Run not found: {req.run}")

        if req.metric not in entry["metrics"]:
            raise HTTPException(400, f"Metric not valid for device: {req.metric}")

        # Load CSV
        csv_path = entry["path"] / req.workload / f"{req.run}.csv"
        df = pd.read_csv(csv_path)

        # Generate signal
        signal = make_signal(
            df=df,
            device_cfg=entry["config"],
            device=req.device,
            workload=req.workload,
            run=req.run,
            metric=req.metric,
            window_size=req.window_size,
        )

        results.append(signal)

    return {"signals": results}

@app.post("/reload")
def reload_registry():
    load_registry()
    return {
        "status": "reloaded",
        "devices": list(DEVICE_REGISTRY.keys())
    }
