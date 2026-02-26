"""
Agent Earth - Configuration & Presets
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

# Adjacency list - defines which regions can trade with each other.
# Ring topology with cross-links.
REGION_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 5],
    1: [0, 2, 3],
    2: [1, 3],
    3: [2, 4, 1],
    4: [3, 5],
    5: [4, 0],
}

# ──────────────────────────────────────────────
# Regional profiles (per-region diversity)
# ──────────────────────────────────────────────
# Productivity multipliers: how fast each resource regenerates per region
# Values > 1 = fertile/productive, < 1 = barren/harsh
REGION_PRODUCTIVITY: Dict[int, Dict[str, float]] = {
    0: {"water": 1.2, "food": 1.0, "energy": 0.8, "land": 1.0},  # Water-rich
    1: {"water": 0.8, "food": 1.3, "energy": 1.0, "land": 1.1},  # Agricultural
    2: {"water": 0.7, "food": 0.7, "energy": 1.5, "land": 0.9},  # Energy hub
    3: {"water": 1.0, "food": 1.0, "energy": 1.0, "land": 1.0},  # Balanced
    4: {"water": 0.6, "food": 0.9, "energy": 0.9, "land": 1.3},  # Land-rich
    5: {"water": 1.1, "food": 1.1, "energy": 0.7, "land": 0.8},  # Coastal
}

# Climate vulnerability per region per disaster type (0-1, higher = more vulnerable)
REGION_CLIMATE_VULNERABILITY: Dict[int, Dict[str, float]] = {
    0: {"drought": 0.3, "flood": 0.8, "energy_crisis": 0.5, "soil_degradation": 0.4},
    1: {"drought": 0.7, "flood": 0.4, "energy_crisis": 0.3, "soil_degradation": 0.6},
    2: {"drought": 0.5, "flood": 0.3, "energy_crisis": 0.8, "soil_degradation": 0.3},
    3: {"drought": 0.5, "flood": 0.5, "energy_crisis": 0.5, "soil_degradation": 0.5},
    4: {"drought": 0.9, "flood": 0.2, "energy_crisis": 0.4, "soil_degradation": 0.8},
    5: {"drought": 0.4, "flood": 0.9, "energy_crisis": 0.6, "soil_degradation": 0.3},
}

# Resource interdependence: production of one resource depends on others
# food_production *= (energy_level / energy_max) * INTERDEPENDENCE["food"]["energy"]
RESOURCE_INTERDEPENDENCE: Dict[str, Dict[str, float]] = {
    "food":   {"energy": 0.3, "land": 0.4},   # food needs energy + land
    "water":  {"energy": 0.2},                 # pumping needs energy
    "energy": {"water": 0.15},                 # cooling needs water
    "land":   {},                               # land is independent
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
# Action definitions (strategy actions)
# ──────────────────────────────────────────────
ACTION_NAMES: List[str] = [
    "hoard",            # 0 - Hoard resources
    "trade",            # 1 - Trade with neighbours
    "invest_growth",    # 2 - Invest in growth
    "conserve",         # 3 - Conserve resources
    "expand_pop",       # 4 - Expand population
]
NUM_ACTIONS: int = len(ACTION_NAMES)

# ──────────────────────────────────────────────
# Trade (learned trade parameters)
# ──────────────────────────────────────────────
TRADE_AMOUNT_BUCKETS: int = 10    # discretized trade amounts (0-9 -> 0%-45% of stock)
TRADE_MAX_FRACTION: float = 0.45  # max fraction of a resource tradeable per step

# Trust dynamics
TRUST_INITIAL: float = 0.5       # starting trust between all region pairs
TRUST_GAIN_PER_TRADE: float = 0.05
TRUST_DECAY_PER_STEP: float = 0.005
TRUST_LOSS_ON_BETRAYAL: float = 0.15
ALLIANCE_THRESHOLD: float = 0.75  # trust above this => alliance
TRADE_ACCEPT_BASE: float = 0.3    # base probability of accepting a trade request

# Legacy rule-based trade (kept for compatibility)
TRADE_SURPLUS_THRESHOLD: float = 0.60
TRADE_DEFICIT_THRESHOLD: float = 0.30
TRADE_TRANSFER_FRAC: float = 0.15

# ──────────────────────────────────────────────
# Population
# ──────────────────────────────────────────────
POP_MIN: float = 10.0
POP_MAX: float = 500.0
POP_GROWTH_RATE: float = 0.02
POP_DECLINE_RATE: float = 0.05

# ──────────────────────────────────────────────
# Resource dynamics
# ──────────────────────────────────────────────
FOOD_REGEN_RATE: float = 0.08
WATER_DECAY_RATE: float = 0.03
ENERGY_DECAY_RATE: float = 0.04
CONSUMPTION_PER_CAPITA: Dict[str, float] = {
    "water": 0.15,
    "food": 0.12,
    "energy": 0.10,
    "land": 0.0,
}

# ──────────────────────────────────────────────
# Climate events
# ──────────────────────────────────────────────
CLIMATE_SEVERITY: float = 1.0

CLIMATE_EVENTS = {
    "drought":          {"prob": 0.10, "resource": "water",  "loss_frac": 0.25},
    "flood":            {"prob": 0.08, "resource": "food",   "loss_frac": 0.20},
    "energy_crisis":    {"prob": 0.07, "resource": "energy", "loss_frac": 0.30},
    "soil_degradation": {"prob": 0.06, "resource": "land",   "loss_frac": 0.15},
}

# ──────────────────────────────────────────────
# Reward weights
# ──────────────────────────────────────────────
REWARD_SURVIVAL: float = 1.0
REWARD_SUSTAINABILITY: float = 0.5
REWARD_POP_STABILITY: float = 0.3
REWARD_COOPERATION: float = 0.4
REWARD_TRADE_SUCCESS: float = 0.3
PENALTY_COLLAPSE: float = -5.0
PENALTY_OVERCONSUMPTION: float = -0.3
PENALTY_BETRAYAL: float = -0.5

SUSTAINABILITY_COLLAPSE: float = 0.10

# ──────────────────────────────────────────────
# Simulation defaults
# ──────────────────────────────────────────────
DEFAULT_TIMESTEPS: int = 500
TRAIN_TIMESTEPS: int = 50_000
DEMO_TRAIN_TIMESTEPS: int = 5_000

# ──────────────────────────────────────────────
# Per-agent observation size
# ──────────────────────────────────────────────
# local: water, food, energy, land, pop, sustainability (6)
# climate_exposure: 4 vulnerability values (4)
# neighbor_avg: 1
# climate_risk: 1
# trade_balance: 1
# trust_to_neighbors (max 3 neighbors shown): 3
# total = 16
OBS_PER_AGENT: int = 16

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
