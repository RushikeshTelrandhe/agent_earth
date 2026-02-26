"""
Agent Earth — Configuration & Presets
======================================
Central configuration for the multi-agent resource scarcity simulator.
All tuneable constants live here so the rest of the codebase stays clean.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List

# ──────────────────────────────────────────────
# World geometry
# ──────────────────────────────────────────────
NUM_REGIONS: int = 6

# Adjacency list — defines which regions can trade with each other.
# By default we use a ring topology with extra cross-links.
REGION_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 5],
    1: [0, 2, 3],
    2: [1, 3],
    3: [2, 4, 1],
    4: [3, 5],
    5: [4, 0],
}

# ──────────────────────────────────────────────
# Resource bounds
# ──────────────────────────────────────────────
RESOURCE_NAMES: List[str] = ["water", "food", "energy", "land"]

RESOURCE_MAX: Dict[str, float] = {
    "water": 100.0,
    "food": 100.0,
    "energy": 100.0,
    "land": 100.0,
}

# ──────────────────────────────────────────────
# Action definitions
# ──────────────────────────────────────────────
ACTION_NAMES: List[str] = [
    "hoard",            # 0 — Hoard resources
    "trade",            # 1 — Trade with neighbours
    "invest_growth",    # 2 — Invest in growth
    "conserve",         # 3 — Conserve resources
    "expand_pop",       # 4 — Expand population
]
NUM_ACTIONS: int = len(ACTION_NAMES)

# ──────────────────────────────────────────────
# Population
# ──────────────────────────────────────────────
POP_MIN: float = 10.0
POP_MAX: float = 500.0
POP_GROWTH_RATE: float = 0.02       # base fractional growth per step
POP_DECLINE_RATE: float = 0.05      # decline when resources scarce

# ──────────────────────────────────────────────
# Resource dynamics
# ──────────────────────────────────────────────
FOOD_REGEN_RATE: float = 0.08       # logistic growth parameter
WATER_DECAY_RATE: float = 0.03      # linear decay per step
ENERGY_DECAY_RATE: float = 0.04     # linear decay per step
CONSUMPTION_PER_CAPITA: Dict[str, float] = {
    "water": 0.15,
    "food": 0.12,
    "energy": 0.10,
    "land": 0.0,                     # land not consumed
}

# ──────────────────────────────────────────────
# Climate events
# ──────────────────────────────────────────────
CLIMATE_SEVERITY: float = 1.0       # global multiplier (slider)

CLIMATE_EVENTS = {
    "drought":       {"prob": 0.10, "resource": "water",  "loss_frac": 0.25},
    "flood":         {"prob": 0.08, "resource": "food",   "loss_frac": 0.20},
    "energy_crisis": {"prob": 0.07, "resource": "energy", "loss_frac": 0.30},
}

# ──────────────────────────────────────────────
# Trade
# ──────────────────────────────────────────────
TRADE_SURPLUS_THRESHOLD: float = 0.60   # fraction of max to count as surplus
TRADE_DEFICIT_THRESHOLD: float = 0.30   # below this = deficit
TRADE_TRANSFER_FRAC: float = 0.15       # fraction of surplus transferred

# ──────────────────────────────────────────────
# Reward weights
# ──────────────────────────────────────────────
REWARD_SURVIVAL: float = 1.0
REWARD_SUSTAINABILITY: float = 0.5
REWARD_POP_STABILITY: float = 0.3
REWARD_COOPERATION: float = 0.4
PENALTY_COLLAPSE: float = -5.0
PENALTY_OVERCONSUMPTION: float = -0.3

# Sustainability collapse threshold
SUSTAINABILITY_COLLAPSE: float = 0.10

# ──────────────────────────────────────────────
# Simulation defaults
# ──────────────────────────────────────────────
DEFAULT_TIMESTEPS: int = 500
TRAIN_TIMESTEPS: int = 50_000

# ──────────────────────────────────────────────
# Presets
# ──────────────────────────────────────────────

@dataclass
class WorldPreset:
    """Encapsulates a named configuration preset."""
    name: str
    water_init: float = 80.0
    food_init: float = 80.0
    energy_init: float = 80.0
    land_init: float = 90.0
    pop_init: float = 100.0
    climate_severity: float = 1.0
    food_regen_rate: float = FOOD_REGEN_RATE
    water_decay_rate: float = WATER_DECAY_RATE
    energy_decay_rate: float = ENERGY_DECAY_RATE


SCARCITY_PRESET = WorldPreset(
    name="scarcity",
    water_init=40.0,
    food_init=35.0,
    energy_init=30.0,
    land_init=50.0,
    pop_init=150.0,
    climate_severity=1.8,
    food_regen_rate=0.04,
    water_decay_rate=0.06,
    energy_decay_rate=0.07,
)

ABUNDANCE_PRESET = WorldPreset(
    name="abundance",
    water_init=95.0,
    food_init=95.0,
    energy_init=90.0,
    land_init=95.0,
    pop_init=80.0,
    climate_severity=0.4,
    food_regen_rate=0.12,
    water_decay_rate=0.01,
    energy_decay_rate=0.02,
)

PRESETS: Dict[str, WorldPreset] = {
    "default": WorldPreset(name="default"),
    "scarcity": SCARCITY_PRESET,
    "abundance": ABUNDANCE_PRESET,
}
