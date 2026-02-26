"""
Crowdsense Detection Store
============================
In-memory capped store for detection metadata.
Computes per-region aggregated signals.
"""

from __future__ import annotations

import time
import threading
from typing import Any, Dict, List

MAX_DETECTIONS = 10000
SIGNAL_WINDOW = 300  # 5-minute window for aggregation

# COCO classes mapped to simulation resource dimensions
POPULATION_CLASSES = {"person"}
ENERGY_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}

_lock = threading.Lock()
_detections: List[Dict[str, Any]] = []


def add_detection(
    user_id: str,
    region_id: int,
    detected_objects: List[Dict],
    frame_object_count: int,
) -> Dict[str, Any]:
    """Store a detection metadata entry."""
    entry = {
        "user_id": user_id,
        "region_id": region_id,
        "timestamp": time.time(),
        "detected_objects": detected_objects,
        "frame_object_count": frame_object_count,
    }
    with _lock:
        _detections.append(entry)
        # Cap size
        if len(_detections) > MAX_DETECTIONS:
            _detections[:] = _detections[-MAX_DETECTIONS:]
    return {"status": "ok", "id": len(_detections)}


def get_region_signals(region_id: int) -> Dict[str, Any]:
    """Compute aggregated signals for a region over the recent window."""
    now = time.time()
    cutoff = now - SIGNAL_WINDOW

    with _lock:
        recent = [
            d for d in _detections
            if d["region_id"] == region_id and d["timestamp"] > cutoff
        ]

    if not recent:
        return {
            "region_id": region_id,
            "population_pressure": 0.0,
            "energy_activity": 0.0,
            "land_utilization": 0.0,
            "food_demand_index": 0.0,
            "sample_count": 0,
            "window_seconds": SIGNAL_WINDOW,
        }

    total_objects = sum(d["frame_object_count"] for d in recent)
    pop_count = 0
    energy_count = 0
    for d in recent:
        for obj in d["detected_objects"]:
            cls = obj.get("class", "").lower()
            if cls in POPULATION_CLASSES:
                pop_count += 1
            if cls in ENERGY_CLASSES:
                energy_count += 1

    n = len(recent)
    land = min(1.0, total_objects / max(1, n * 10))
    pop = min(1.0, pop_count / max(1, n * 5))
    energy = min(1.0, energy_count / max(1, n * 3))
    food = min(1.0, (land + pop + energy) / 3.0)

    return {
        "region_id": region_id,
        "population_pressure": round(pop, 3),
        "energy_activity": round(energy, 3),
        "land_utilization": round(land, 3),
        "food_demand_index": round(food, 3),
        "sample_count": n,
        "window_seconds": SIGNAL_WINDOW,
    }


def get_all_region_signals() -> List[Dict[str, Any]]:
    """Get signals for all 6 regions."""
    return [get_region_signals(i) for i in range(6)]


def get_stats() -> Dict[str, Any]:
    """System health stats."""
    with _lock:
        total = len(_detections)
        regions = {}
        for d in _detections:
            rid = d["region_id"]
            regions[rid] = regions.get(rid, 0) + 1
    return {"total_detections": total, "per_region": regions}
