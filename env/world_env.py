"""
Agent Earth — Gymnasium Custom Environment
=============================================
Multi-region world with finite resources, dynamic population,
trade mechanics, and multi-objective reward.

Observation : flattened vector of per-region state
Action      : MultiDiscrete — one discrete action per region
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from events.disasters import DisasterEngine
from utils.config import (
    ACTION_NAMES,
    CONSUMPTION_PER_CAPITA,
    ENERGY_DECAY_RATE,
    FOOD_REGEN_RATE,
    NUM_ACTIONS,
    NUM_REGIONS,
    PENALTY_COLLAPSE,
    PENALTY_OVERCONSUMPTION,
    POP_DECLINE_RATE,
    POP_GROWTH_RATE,
    POP_MAX,
    POP_MIN,
    REGION_ADJACENCY,
    RESOURCE_MAX,
    RESOURCE_NAMES,
    REWARD_COOPERATION,
    REWARD_POP_STABILITY,
    REWARD_SURVIVAL,
    REWARD_SUSTAINABILITY,
    SUSTAINABILITY_COLLAPSE,
    TRADE_DEFICIT_THRESHOLD,
    TRADE_SURPLUS_THRESHOLD,
    TRADE_TRANSFER_FRAC,
    WATER_DECAY_RATE,
    WorldPreset,
)

# ──────────────────────────────────────────────
# Per-region observation features
# ──────────────────────────────────────────────
#   water, food, energy, land, population,
#   sustainability, neighbor_avg, climate_risk, trade_balance
OBS_PER_REGION = 9


class WorldEnv(gym.Env):
    """Multi-agent resource scarcity environment.

    One shared policy outputs an action vector (one action per region).
    """

    metadata = {"render_modes": ["human"]}

    def __init__(
        self,
        num_regions: int = NUM_REGIONS,
        preset: Optional[WorldPreset] = None,
        max_steps: int = 500,
        climate_severity: float = 1.0,
        seed: int | None = None,
    ) -> None:
        super().__init__()

        self.num_regions = num_regions
        self.max_steps = max_steps
        self.preset = preset or WorldPreset(name="default")
        self.climate_severity = climate_severity

        # Spaces
        self.observation_space = spaces.Box(
            low=0.0,
            high=1.0,
            shape=(num_regions * OBS_PER_REGION,),
            dtype=np.float32,
        )
        self.action_space = spaces.MultiDiscrete([NUM_ACTIONS] * num_regions)

        # Disaster engine
        self.disaster_engine = DisasterEngine(severity=climate_severity, seed=seed)

        # Internal state (set in reset)
        self.regions: List[Dict[str, float]] = []
        self.trade_log: List[Dict[str, Any]] = []
        self.current_step: int = 0
        self.np_random: np.random.Generator = np.random.default_rng(seed)

    # ──────────────────────────────────────────
    # Reset
    # ──────────────────────────────────────────
    def reset(
        self,
        seed: int | None = None,
        options: Optional[dict] = None,
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        super().reset(seed=seed)
        if seed is not None:
            self.np_random = np.random.default_rng(seed)

        p = self.preset
        self.regions = []
        for i in range(self.num_regions):
            # Slight per-region randomness so behaviour diverges
            noise = lambda v: float(np.clip(v + self.np_random.uniform(-5, 5), 1, 100))
            self.regions.append({
                "id": i,
                "water": noise(p.water_init),
                "food": noise(p.food_init),
                "energy": noise(p.energy_init),
                "land": noise(p.land_init),
                "population": float(np.clip(p.pop_init + self.np_random.uniform(-20, 20), POP_MIN, POP_MAX)),
                "sustainability": 0.8,
                "trade_balance": 0.0,
                "action_history": [],
                "collapsed": False,
            })
        self.trade_log = []
        self.current_step = 0
        return self._get_obs(), self._get_info()

    # ──────────────────────────────────────────
    # Step
    # ──────────────────────────────────────────
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        self.current_step += 1

        # 1 — Apply actions
        self._apply_actions(action)

        # 2 — Resource dynamics (consumption + regeneration)
        self._update_resources()

        # 3 — Climate events
        disaster_outcomes, event_names = self.disaster_engine.sample_events(self.num_regions)
        for outcome in disaster_outcomes:
            r = self.regions[outcome.region_id]
            r[outcome.resource] = max(0.0, r[outcome.resource] * (1.0 - outcome.loss_amount))

        # 4 — Trade
        trades_this_step = self._execute_trades(action)

        # 5 — Population dynamics
        self._update_population()

        # 6 — Sustainability scores
        self._update_sustainability()

        # 7 — Collapse check
        self._check_collapse()

        # 8 — Reward
        reward = self._compute_reward(action, trades_this_step)

        # 9 — Termination
        terminated = self.current_step >= self.max_steps
        truncated = False
        all_collapsed = all(r["collapsed"] for r in self.regions)
        if all_collapsed:
            terminated = True

        info = self._get_info()
        info["events"] = event_names
        info["trades"] = trades_this_step

        return self._get_obs(), reward, terminated, truncated, info

    # ──────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────
    def _apply_actions(self, actions: np.ndarray) -> None:
        """Modify region state based on chosen actions."""
        for i, act in enumerate(actions):
            r = self.regions[i]
            if r["collapsed"]:
                continue
            r["action_history"].append(int(act))
            if act == 0:  # Hoard
                # Slight resource boost, sustainability hit
                for res in RESOURCE_NAMES:
                    r[res] = min(RESOURCE_MAX[res], r[res] * 1.02)
                r["sustainability"] = max(0, r["sustainability"] - 0.02)
            elif act == 1:  # Trade — handled separately
                pass
            elif act == 2:  # Invest in growth
                r["food"] = min(RESOURCE_MAX["food"], r["food"] * 1.05)
                r["energy"] = min(RESOURCE_MAX["energy"], r["energy"] * 1.03)
                r["sustainability"] += 0.01
            elif act == 3:  # Conserve
                r["sustainability"] = min(1.0, r["sustainability"] + 0.03)
                # Slight slow-down in consumption handled in _update_resources
            elif act == 4:  # Expand population
                r["population"] = min(POP_MAX, r["population"] * 1.04)

    # ──────────────────────────────────────────
    # Resource dynamics
    # ──────────────────────────────────────────
    def _update_resources(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            pop = r["population"]

            # Consumption
            conserve_mult = 0.7 if (r["action_history"] and r["action_history"][-1] == 3) else 1.0
            r["water"] = max(0.0, r["water"] - pop * CONSUMPTION_PER_CAPITA["water"] * conserve_mult)
            r["food"]  = max(0.0, r["food"]  - pop * CONSUMPTION_PER_CAPITA["food"]  * conserve_mult)
            r["energy"]= max(0.0, r["energy"]- pop * CONSUMPTION_PER_CAPITA["energy"] * conserve_mult)

            # Regeneration
            # Food — logistic growth
            food_cap = RESOURCE_MAX["food"]
            r["food"] = min(food_cap, r["food"] + self.preset.food_regen_rate * r["food"] * (1 - r["food"] / food_cap))

            # Water — linear decay + small natural replenishment
            r["water"] = max(0.0, r["water"] - self.preset.water_decay_rate * r["water"] + 1.5)

            # Energy — linear decay + small replenishment
            r["energy"] = max(0.0, r["energy"] - self.preset.energy_decay_rate * r["energy"] + 1.0)

            # Clamp
            for res in RESOURCE_NAMES:
                r[res] = float(np.clip(r[res], 0.0, RESOURCE_MAX[res]))

    # ──────────────────────────────────────────
    # Trade system
    # ──────────────────────────────────────────
    def _execute_trades(self, actions: np.ndarray) -> List[Dict[str, Any]]:
        """Hybrid trade: regions choosing 'trade' share surplus with deficit neighbours."""
        trades: List[Dict[str, Any]] = []
        for i, act in enumerate(actions):
            if act != 1 or self.regions[i]["collapsed"]:
                continue
            neighbours = REGION_ADJACENCY.get(i % len(REGION_ADJACENCY), [])
            for res in RESOURCE_NAMES:
                surplus = self.regions[i][res] - TRADE_SURPLUS_THRESHOLD * RESOURCE_MAX[res]
                if surplus <= 0:
                    continue
                for nb in neighbours:
                    if nb >= self.num_regions:
                        continue
                    deficit = TRADE_DEFICIT_THRESHOLD * RESOURCE_MAX[res] - self.regions[nb][res]
                    if deficit > 0:
                        transfer = min(surplus * TRADE_TRANSFER_FRAC, deficit)
                        self.regions[i][res] -= transfer
                        self.regions[nb][res] = min(RESOURCE_MAX[res], self.regions[nb][res] + transfer)
                        self.regions[i]["trade_balance"] += transfer
                        self.regions[nb]["trade_balance"] -= transfer
                        trades.append({
                            "from": i, "to": nb,
                            "resource": res, "amount": round(transfer, 2),
                        })
        self.trade_log.extend(trades)
        return trades

    # ──────────────────────────────────────────
    # Population dynamics
    # ──────────────────────────────────────────
    def _update_population(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            avg_resource = np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES])
            if avg_resource > 0.4:
                r["population"] = min(POP_MAX, r["population"] * (1 + POP_GROWTH_RATE * avg_resource))
            else:
                r["population"] = max(POP_MIN, r["population"] * (1 - POP_DECLINE_RATE * (1 - avg_resource)))

    # ──────────────────────────────────────────
    # Sustainability
    # ──────────────────────────────────────────
    def _update_sustainability(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            resource_health = np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES])
            pop_pressure = r["population"] / POP_MAX
            # Sustainability trends toward resource health minus population pressure
            target = max(0.0, min(1.0, resource_health - 0.3 * pop_pressure))
            r["sustainability"] += 0.1 * (target - r["sustainability"])
            r["sustainability"] = float(np.clip(r["sustainability"], 0.0, 1.0))

    # ──────────────────────────────────────────
    # Collapse check
    # ──────────────────────────────────────────
    def _check_collapse(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            total_resources = sum(r[res] for res in RESOURCE_NAMES)
            if total_resources < 5.0 or r["sustainability"] < SUSTAINABILITY_COLLAPSE:
                r["collapsed"] = True

    # ──────────────────────────────────────────
    # Reward function
    # ──────────────────────────────────────────
    def _compute_reward(self, actions: np.ndarray, trades: List[Dict[str, Any]]) -> float:
        reward = 0.0
        for i, r in enumerate(self.regions):
            if r["collapsed"]:
                reward += PENALTY_COLLAPSE
                continue

            # Survival bonus
            reward += REWARD_SURVIVAL

            # Sustainability
            reward += REWARD_SUSTAINABILITY * r["sustainability"]

            # Population stability (lower variance = better)
            pop_ratio = r["population"] / POP_MAX
            reward += REWARD_POP_STABILITY * (1.0 - abs(pop_ratio - 0.4))

            # Overconsumption penalty
            avg_res = np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES])
            if avg_res < 0.2:
                reward += PENALTY_OVERCONSUMPTION

        # Cooperation bonus — proportional to number of trades
        reward += REWARD_COOPERATION * len(trades)

        return float(reward)

    # ──────────────────────────────────────────
    # Observations
    # ──────────────────────────────────────────
    def _get_obs(self) -> np.ndarray:
        obs = []
        for i, r in enumerate(self.regions):
            # Normalised resource levels
            water_n  = r["water"]  / RESOURCE_MAX["water"]
            food_n   = r["food"]   / RESOURCE_MAX["food"]
            energy_n = r["energy"] / RESOURCE_MAX["energy"]
            land_n   = r["land"]   / RESOURCE_MAX["land"]
            pop_n    = r["population"] / POP_MAX
            sust     = r["sustainability"]

            # Neighbour average resources
            neighbours = REGION_ADJACENCY.get(i % len(REGION_ADJACENCY), [])
            if neighbours:
                nb_avg = float(np.mean([
                    np.mean([self.regions[nb][res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES])
                    for nb in neighbours if nb < self.num_regions
                ])) if neighbours else 0.0
            else:
                nb_avg = 0.0

            # Climate risk — proxy: current severity
            climate_risk = min(1.0, self.disaster_engine.severity / 3.0)

            # Trade balance (normalised, clipped)
            trade_bal = float(np.clip(r["trade_balance"] / 100.0, -1.0, 1.0))

            obs.extend([water_n, food_n, energy_n, land_n, pop_n, sust, nb_avg, climate_risk, trade_bal])

        return np.array(obs, dtype=np.float32)

    def _get_info(self) -> Dict[str, Any]:
        return {
            "step": self.current_step,
            "regions": [
                {
                    "id": r["id"],
                    "water": round(r["water"], 2),
                    "food": round(r["food"], 2),
                    "energy": round(r["energy"], 2),
                    "land": round(r["land"], 2),
                    "population": round(r["population"], 2),
                    "sustainability": round(r["sustainability"], 3),
                    "collapsed": r["collapsed"],
                    "trade_balance": round(r["trade_balance"], 2),
                    "last_action": ACTION_NAMES[r["action_history"][-1]] if r["action_history"] else "none",
                }
                for r in self.regions
            ],
        }

    # ──────────────────────────────────────────
    # Render (text)
    # ──────────────────────────────────────────
    def render(self) -> None:
        print(f"\n{'='*60}")
        print(f"  Step {self.current_step}")
        print(f"{'='*60}")
        for r in self.regions:
            status = "COLLAPSED" if r["collapsed"] else "active"
            print(
                f"  Region {r['id']} [{status}]  "
                f"W:{r['water']:.1f}  F:{r['food']:.1f}  E:{r['energy']:.1f}  "
                f"L:{r['land']:.1f}  Pop:{r['population']:.0f}  "
                f"Sust:{r['sustainability']:.2f}"
            )
