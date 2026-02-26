"""
Agent Earth — Simulation Logger
================================
Records world state every step and persists runs to JSON / CSV.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional


class SimulationLogger:
    """Collects per-step snapshots and writes them to disk."""

    def __init__(self, output_dir: str = "results") -> None:
        self.output_dir = output_dir
        self.steps: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
        os.makedirs(output_dir, exist_ok=True)

    # ── recording ──────────────────────────────
    def set_metadata(self, **kwargs: Any) -> None:
        """Store run-level metadata (preset, timesteps, etc.)."""
        self.metadata.update(kwargs)

    def log_step(self, step: int, world_state: Dict[str, Any]) -> None:
        """Append a snapshot for the given timestep."""
        record: Dict[str, Any] = {"step": step, **world_state}
        self.steps.append(record)

    # ── persistence ────────────────────────────
    def save_json(self, filename: Optional[str] = None) -> str:
        """Save the full run (metadata + steps) to a JSON file."""
        filename = filename or f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
        path = os.path.join(self.output_dir, filename)
        payload = {
            "metadata": self.metadata,
            "steps": self.steps,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=str)
        return path

    def save_csv(self, filename: Optional[str] = None) -> str:
        """Save flattened step data to CSV (one row per region per step)."""
        filename = filename or f"run_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = os.path.join(self.output_dir, filename)

        if not self.steps:
            return path

        # Flatten: each step has a 'regions' list; explode into rows
        rows: List[Dict[str, Any]] = []
        for record in self.steps:
            step_num = record["step"]
            regions = record.get("regions", [])
            events = record.get("events", [])
            for region in regions:
                row = {"step": step_num, **region, "events": ";".join(events)}
                rows.append(row)

        if rows:
            fieldnames = list(rows[0].keys())
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        return path

    # ── loading ─────────────────────────────────
    @classmethod
    def load_json(cls, path: str) -> "SimulationLogger":
        """Reconstruct a logger from a saved JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger = cls()
        logger.metadata = data.get("metadata", {})
        logger.steps = data.get("steps", [])
        return logger

    # ── insights summary ───────────────────────
    def save_insights(self, insights: Dict[str, Any], filename: str = "insights.txt") -> str:
        """Write a human-readable insights summary to disk."""
        path = os.path.join(self.output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("  Agent Earth — Simulation Insights\n")
            f.write("=" * 60 + "\n\n")
            for key, value in insights.items():
                f.write(f"  {key}: {value}\n")
            f.write("\n" + "=" * 60 + "\n")
        return path

    def clear(self) -> None:
        """Reset the logger for a fresh run."""
        self.steps.clear()
        self.metadata.clear()
