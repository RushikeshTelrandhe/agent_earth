"""
Crowdsense RL Adapter
======================
Non-destructive adapter that translates crowdsense signals
into RL-interpretable modifiers. Does NOT modify core RL logic.
"""

from __future__ import annotations

from typing import Any, Dict
from crowdsense.store import get_region_signals


def get_rl_modifiers(region_id: int) -> Dict[str, Any]:
    """Return parameter modifiers based on crowdsense signals.

    These are multipliers/offsets that can be read by the advisor
    or optionally fed into the environment. They do NOT automatically
    change the simulation — they're informational.

    Returns
    -------
    dict with keys like population_pressure_mod, resource_consumption_mod, etc.
    """
    signals = get_region_signals(region_id)

    # No data → neutral modifiers
    if signals["sample_count"] == 0:
        return {
            "region_id": region_id,
            "has_data": False,
            "population_pressure": 1.0,
            "energy_usage_proxy": 1.0,
            "land_activity_index": 1.0,
            "food_demand_modifier": 1.0,
            "label": "No sensing data",
        }

    pop = signals["population_pressure"]
    energy = signals["energy_activity"]
    land = signals["land_utilization"]
    food = signals["food_demand_index"]

    # Derive modifiers (small perturbations, ±15% max)
    pop_mod = 1.0 + pop * 0.15
    energy_mod = 1.0 + energy * 0.12
    land_mod = 1.0 + land * 0.10
    food_mod = 1.0 + food * 0.10

    activity = (pop + energy + land + food) / 4.0
    if activity > 0.7:
        label = "High resource pressure detected"
    elif activity > 0.3:
        label = "Moderate resource activity"
    else:
        label = "Low resource activity"

    return {
        "region_id": region_id,
        "has_data": True,
        "population_pressure": round(pop_mod, 3),
        "energy_usage_proxy": round(energy_mod, 3),
        "land_activity_index": round(land_mod, 3),
        "food_demand_modifier": round(food_mod, 3),
        "signals": signals,
        "label": label,
    }


def get_all_modifiers() -> list:
    """Get modifiers for all 6 regions."""
    return [get_rl_modifiers(i) for i in range(6)]
