"""
Agent Earth - Climate Disaster Engine
=======================================
Probabilistic climate events with per-region vulnerability.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from utils.config import (
    CLIMATE_EVENTS, CLIMATE_SEVERITY, NUM_REGIONS,
    REGION_CLIMATE_VULNERABILITY,
)


@dataclass
class DisasterOutcome:
    """Result of a disaster hitting a region."""
    event_name: str
    region_id: int
    resource: str
    loss_amount: float


class DisasterEngine:
    """Generates stochastic climate events with per-region vulnerability.

    Parameters
    ----------
    severity : float
        Global severity multiplier (1.0 = baseline).
    seed : int | None
        Optional RNG seed for reproducibility.
    """

    def __init__(self, severity: float = CLIMATE_SEVERITY, seed: int | None = None) -> None:
        self.severity = severity
        self.rng = random.Random(seed)
        self.events: Dict[str, Dict[str, Any]] = dict(CLIMATE_EVENTS)
        # Track which regions were hit each step (for analysis)
        self.last_hits: Dict[int, List[str]] = {}

    def set_severity(self, severity: float) -> None:
        """Update global climate severity."""
        self.severity = max(0.0, severity)

    def sample_events(self, num_regions: int) -> Tuple[List[DisasterOutcome], List[str]]:
        """Roll for disasters across all regions for one timestep.

        Returns
        -------
        outcomes : list[DisasterOutcome]
            Individual region-level impacts.
        event_names : list[str]
            Global event labels that fired this step.
        """
        outcomes: List[DisasterOutcome] = []
        event_names: List[str] = []
        self.last_hits = {i: [] for i in range(num_regions)}

        for event_name, info in self.events.items():
            # Global probability scaled by severity
            prob = info["prob"] * self.severity
            if self.rng.random() < prob:
                event_names.append(event_name)
                # Per-region: hit probability scales with region vulnerability
                for region_id in range(num_regions):
                    vuln = self._get_vulnerability(region_id, event_name)
                    hit_prob = 0.4 + 0.5 * vuln  # range [0.4, 0.9] based on vulnerability
                    if self.rng.random() < hit_prob:
                        # Loss scales with both severity and regional vulnerability
                        loss_frac = info["loss_frac"] * self.severity * (0.6 + 0.4 * vuln)
                        outcomes.append(
                            DisasterOutcome(
                                event_name=event_name,
                                region_id=region_id,
                                resource=info["resource"],
                                loss_amount=loss_frac,
                            )
                        )
                        self.last_hits[region_id].append(event_name)
        return outcomes, event_names

    def _get_vulnerability(self, region_id: int, event_name: str) -> float:
        """Get climate vulnerability for a region and event type."""
        if region_id in REGION_CLIMATE_VULNERABILITY:
            return REGION_CLIMATE_VULNERABILITY[region_id].get(event_name, 0.5)
        return 0.5  # default moderate vulnerability

    def get_region_exposure(self, region_id: int) -> Dict[str, float]:
        """Return climate exposure vector for a region (for observations)."""
        if region_id in REGION_CLIMATE_VULNERABILITY:
            return dict(REGION_CLIMATE_VULNERABILITY[region_id])
        return {"drought": 0.5, "flood": 0.5, "energy_crisis": 0.5, "soil_degradation": 0.5}
