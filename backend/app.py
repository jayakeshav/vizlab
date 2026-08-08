from fastapi import FastAPI, HTTPException
from pathlib import Path
import pandas as pd
import numpy as np
import json
from pydantic import BaseModel
from typing import List, Dict, Any


app = FastAPI(title="VizLab API")


DATA_ROOT = Path(__file__).parent.parent / "Master_Data_Sets"

DEVICE_REGISTRY = {}

@app.on_event("startup")
def load_registry():
    global DEVICE_REGISTRY
    DEVICE_REGISTRY.clear()

    for device_base_dir in DATA_ROOT.iterdir():
        if not device_base_dir.is_dir() or device_base_dir.name.startswith('.'):
            continue

        for variant_dir in device_base_dir.iterdir():
            if not variant_dir.is_dir() or variant_dir.name.startswith('.'):
                continue

            cfg_path = variant_dir / "device_config.json"
            if not cfg_path.exists():
                continue  # skip if no config

            with open(cfg_path) as f:
                device_cfg = json.load(f)

            # metrics come ONLY from config (preserve batch order)
            metrics = []
            seen_metrics = set()
            for batch in device_cfg["batches"].values():
                for metric in batch["metrics"]:
                    if metric not in seen_metrics:
                        metrics.append(metric)
                        seen_metrics.add(metric)

            workloads = {}
            for workload_dir in variant_dir.iterdir():
                if not workload_dir.is_dir() or workload_dir.name.startswith('.'):
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

            registry_key = f"{device_base_dir.name}_{variant_dir.name}"
            DEVICE_REGISTRY[registry_key] = {
                "path": variant_dir,
                "config": device_cfg,
                "metrics": metrics,
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
    variant: str
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
    return sorted(list(set(k.rsplit("_", 1)[0] for k in DEVICE_REGISTRY.keys())))

@app.get("/variants")
def list_variants(device: str):
    variants = []
    for k in DEVICE_REGISTRY.keys():
        if k.startswith(f"{device}_"):
            variants.append(k.rsplit("_", 1)[1])
    return sorted(variants)

@app.get("/metrics")
def list_metrics(device: str, variant: str):
    key = f"{device}_{variant}"
    if key not in DEVICE_REGISTRY:
        raise HTTPException(404, f"Device/Variant not found: {key}")
    return DEVICE_REGISTRY[key]["metrics"]

@app.get("/workloads")
def list_workloads(device: str, variant: str):
    key = f"{device}_{variant}"
    if key not in DEVICE_REGISTRY:
        raise HTTPException(404, f"Device/Variant not found: {key}")
    return sorted(DEVICE_REGISTRY[key]["workloads"].keys())

@app.get("/runs")
def list_runs(device: str, variant: str, workload: str):
    key = f"{device}_{variant}"
    if key not in DEVICE_REGISTRY:
        raise HTTPException(404, f"Device/Variant not found: {key}")

    entry = DEVICE_REGISTRY[key]
    if workload not in entry["workloads"]:
        raise HTTPException(404, "Workload not found")

    runs = list(entry["workloads"][workload]["runs"])

    if variant != "benign":
        benign_key = f"{device}_benign"
        if benign_key in DEVICE_REGISTRY:
            benign_entry = DEVICE_REGISTRY[benign_key]
            if workload in benign_entry["workloads"]:
                runs.extend(benign_entry["workloads"][workload]["runs"])

    return sorted(runs)


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

    is_benign = "benign" in run.lower()
    if is_benign:
        labels = np.zeros(len(df), dtype=int)
        batch_name = "default"
    else:
        labels = derive_labels(df, device_cfg, metric)
        batch_name = find_metric_batch(device_cfg, metric)

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
            "batch": batch_name,
        },
        "transform": {
            "window_size": window_size,
            "aggregation": "none",
        },
    }

@app.get("/signal", response_model=Signal)
def get_signal(
    device: str,
    variant: str,
    workload: str,
    run: str,
    metric: str,
    window_size: int = 1,
):
    key = f"{device}_{variant}"
    if key not in DEVICE_REGISTRY:
        raise HTTPException(404, f"Device/Variant not found: {key}")

    entry = DEVICE_REGISTRY[key]

    if metric not in entry["metrics"]:
        raise HTTPException(400, f"Metric not valid for device: {metric}")

    # Determine CSV path
    if "benign" in run.lower():
        benign_key = f"{device}_benign"
        if benign_key not in DEVICE_REGISTRY:
            raise HTTPException(404, f"Benign variant not found for device: {device}")
        path_entry = DEVICE_REGISTRY[benign_key]
    else:
        path_entry = entry

    csv_path = path_entry["path"] / workload / f"{run}.csv"
    if not csv_path.exists():
        raise HTTPException(404, f"Run file not found: {csv_path}")

    df = pd.read_csv(csv_path)

    # Core logic
    return make_signal(
        df=df,
        device_cfg=entry["config"],
        device=key,
        workload=workload,
        run=run,
        metric=metric,
        window_size=window_size,
    )


@app.post("/signals", response_model=SignalsResponse)
def get_signals(payload: SignalsRequest):
    results = []

    for req in payload.requests:
        key = f"{req.device}_{req.variant}"
        if key not in DEVICE_REGISTRY:
            raise HTTPException(404, f"Device/Variant not found: {key}")

        entry = DEVICE_REGISTRY[key]

        if req.metric not in entry["metrics"]:
            raise HTTPException(400, f"Metric not valid for device: {req.metric}")

        # Determine CSV path
        if "benign" in req.run.lower():
            benign_key = f"{req.device}_benign"
            if benign_key not in DEVICE_REGISTRY:
                raise HTTPException(404, f"Benign variant not found for device: {req.device}")
            path_entry = DEVICE_REGISTRY[benign_key]
        else:
            path_entry = entry

        csv_path = path_entry["path"] / req.workload / f"{req.run}.csv"
        if not csv_path.exists():
            raise HTTPException(404, f"Run file not found: {csv_path}")

        df = pd.read_csv(csv_path)

        # Generate signal
        signal = make_signal(
            df=df,
            device_cfg=entry["config"],
            device=key,
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

# Auto-initialize registry when imported or run
load_registry()
