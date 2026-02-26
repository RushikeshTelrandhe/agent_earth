"""
Agent Earth — Climate Disaster Engine
=======================================
Probabilistic climate events that impact regional resources.
Uses weighted random sampling each timestep.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

from utils.config import CLIMATE_EVENTS, CLIMATE_SEVERITY


@dataclass
class DisasterOutcome:
    """Result of a disaster hitting a region."""
    event_name: str
    region_id: int
    resource: str
    loss_amount: float


class DisasterEngine:
    """Generates stochastic climate events per timestep.

    Parameters
    ----------
    severity : float
        Global severity multiplier (1.0 = baseline).  Controlled via
        dashboard slider at runtime.
    seed : int | None
        Optional RNG seed for reproducibility.
    """

    def __init__(self, severity: float = CLIMATE_SEVERITY, seed: int | None = None) -> None:
        self.severity = severity
        self.rng = random.Random(seed)
        # Build event table from config
        self.events: Dict[str, Dict[str, Any]] = dict(CLIMATE_EVENTS)

    def set_severity(self, severity: float) -> None:
        """Update global climate severity (e.g. from slider)."""
        self.severity = max(0.0, severity)

    def sample_events(self, num_regions: int) -> Tuple[List[DisasterOutcome], List[str]]:
        """Roll for disasters across all regions for one timestep.

        Returns
        -------
        outcomes : list[DisasterOutcome]
            Individual region-level impacts.
        event_names : list[str]
            Global event labels that fired this step (for logging).
        """
        outcomes: List[DisasterOutcome] = []
        event_names: List[str] = []

        for event_name, info in self.events.items():
            # Probability scaled by severity
            prob = info["prob"] * self.severity
            if self.rng.random() < prob:
                event_names.append(event_name)
                # Affect each region independently with 60% chance
                for region_id in range(num_regions):
                    if self.rng.random() < 0.6:
                        loss_frac = info["loss_frac"] * self.severity
                        outcomes.append(
                            DisasterOutcome(
                                event_name=event_name,
                                region_id=region_id,
                                resource=info["resource"],
                                loss_amount=loss_frac,
                            )
                        )
        return outcomes, event_names
