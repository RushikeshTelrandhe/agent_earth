"""
Agent Earth - Multi-Agent World Environment
=============================================
Multi-region world with learned trade, trust dynamics,
per-region rewards, and climate-driven behavioral divergence.

Each region is an independent agent. The environment accepts
a dict of actions {region_id: action_array} and returns
per-region observations and rewards.
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
    ALLIANCE_THRESHOLD,
    CONSUMPTION_PER_CAPITA,
    ENERGY_DECAY_RATE,
    FOOD_REGEN_RATE,
    NUM_ACTIONS,
    NUM_REGIONS,
    OBS_PER_AGENT,
    PENALTY_BETRAYAL,
    PENALTY_COLLAPSE,
    PENALTY_OVERCONSUMPTION,
    POP_DECLINE_RATE,
    POP_GROWTH_RATE,
    POP_MAX,
    POP_MIN,
    REGION_ADJACENCY,
    REGION_CLIMATE_VULNERABILITY,
    REGION_PRODUCTIVITY,
    RESOURCE_INTERDEPENDENCE,
    RESOURCE_MAX,
    RESOURCE_NAMES,
    REWARD_COOPERATION,
    REWARD_POP_STABILITY,
    REWARD_SURVIVAL,
    REWARD_SUSTAINABILITY,
    REWARD_TRADE_SUCCESS,
    SUSTAINABILITY_COLLAPSE,
    TRADE_ACCEPT_BASE,
    TRADE_AMOUNT_BUCKETS,
    TRADE_MAX_FRACTION,
    TRUST_DECAY_PER_STEP,
    TRUST_GAIN_PER_TRADE,
    TRUST_INITIAL,
    TRUST_LOSS_ON_BETRAYAL,
    WATER_DECAY_RATE,
    WorldPreset,
)


class WorldEnv(gym.Env):
    """Multi-agent resource scarcity environment.

    Supports both:
    - Legacy shared mode: flat obs + MultiDiscrete actions
    - Multi-agent mode: per-region obs/actions/rewards via step_multi()
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

        # Per-agent action: [strategy(0-4), trade_target(0-N-1), trade_resource(0-3), trade_amount(0-9)]
        self.agent_action_dims = [NUM_ACTIONS, num_regions, len(RESOURCE_NAMES), TRADE_AMOUNT_BUCKETS]

        # Legacy flat spaces (for shared-mode backward compatibility)
        self.observation_space = spaces.Box(
            low=0.0, high=1.0,
            shape=(num_regions * OBS_PER_AGENT,),
            dtype=np.float32,
        )
        self.action_space = spaces.MultiDiscrete(
            [NUM_ACTIONS] * num_regions
        )

        # Disaster engine
        self.disaster_engine = DisasterEngine(severity=climate_severity, seed=seed)

        # Internal state
        self.regions: List[Dict[str, Any]] = []
        self.trade_log: List[Dict[str, Any]] = []
        self.trust_matrix: np.ndarray = np.full((num_regions, num_regions), TRUST_INITIAL)
        self.alliances: Dict[Tuple[int, int], int] = {}  # (i,j) -> formed_at_step
        self.cooperation_streaks: Dict[Tuple[int, int], int] = {}
        self.betrayal_log: List[Dict[str, Any]] = []
        self.current_step: int = 0
        self.per_region_rewards: Dict[int, float] = {}
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
                "climate_exposure": self.disaster_engine.get_region_exposure(i),
                "trade_partners": [],
                "collapse_cause": None,
            })
        self.trade_log = []
        self.trust_matrix = np.full((self.num_regions, self.num_regions), TRUST_INITIAL)
        np.fill_diagonal(self.trust_matrix, 1.0)
        self.alliances = {}
        self.cooperation_streaks = {}
        self.betrayal_log = []
        self.current_step = 0
        self.per_region_rewards = {i: 0.0 for i in range(self.num_regions)}
        return self._get_flat_obs(), self._get_info()

    # ──────────────────────────────────────────
    # Multi-agent step (primary interface)
    # ──────────────────────────────────────────
    def step_multi(
        self, actions: Dict[int, np.ndarray]
    ) -> Tuple[Dict[int, np.ndarray], Dict[int, float], bool, bool, Dict[str, Any]]:
        """Step with per-agent actions.

        Parameters
        ----------
        actions : dict[int, ndarray]
            {region_id: [strategy, trade_target, trade_resource, trade_amount]}

        Returns
        -------
        observations, rewards, terminated, truncated, info
        """
        self.current_step += 1

        # 1 - Parse and apply strategy actions
        strategy_actions = np.array([
            int(actions.get(i, [0, 0, 0, 0])[0]) for i in range(self.num_regions)
        ])
        self._apply_actions(strategy_actions)

        # 2 - Resource dynamics with interdependence
        self._update_resources()

        # 3 - Climate events
        disaster_outcomes, event_names = self.disaster_engine.sample_events(self.num_regions)
        for outcome in disaster_outcomes:
            r = self.regions[outcome.region_id]
            if not r["collapsed"]:
                r[outcome.resource] = max(0.0, r[outcome.resource] * (1.0 - outcome.loss_amount))

        # 4 - Learned trade execution
        trades_this_step = self._execute_learned_trades(actions)

        # 5 - Trust decay
        self._decay_trust()

        # 6 - Population dynamics
        self._update_population()

        # 7 - Sustainability
        self._update_sustainability()

        # 8 - Collapse check
        self._check_collapse()

        # 9 - Alliance updates
        self._update_alliances()

        # 10 - Per-region rewards
        self.per_region_rewards = self._compute_per_region_rewards(actions, trades_this_step)

        # 11 - Termination
        terminated = self.current_step >= self.max_steps
        truncated = False
        if all(r["collapsed"] for r in self.regions):
            terminated = True

        info = self._get_info()
        info["events"] = event_names
        info["trades"] = trades_this_step
        info["trust_matrix"] = self.trust_matrix.tolist()
        info["alliances"] = [
            {"pair": list(pair), "since": step}
            for pair, step in self.alliances.items()
        ]

        # Per-agent observations
        per_agent_obs = {i: self._get_agent_obs(i) for i in range(self.num_regions)}

        return per_agent_obs, self.per_region_rewards, terminated, truncated, info

    # Legacy shared-mode step (backward compatibility)
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Legacy step: accepts flat MultiDiscrete and returns global reward."""
        # Convert flat actions to multi-agent format
        multi_actions = {}
        for i in range(self.num_regions):
            strategy = int(action[i]) if i < len(action) else 0
            # Auto-select trade target as random neighbor for legacy mode
            neighbors = REGION_ADJACENCY.get(i % len(REGION_ADJACENCY), [0])
            target = neighbors[self.np_random.integers(len(neighbors))] if neighbors else 0
            multi_actions[i] = np.array([strategy, target, 0, 5])

        obs_dict, rewards_dict, terminated, truncated, info = self.step_multi(multi_actions)

        global_reward = sum(rewards_dict.values())
        return self._get_flat_obs(), global_reward, terminated, truncated, info

    # ──────────────────────────────────────────
    # Actions
    # ──────────────────────────────────────────
    def _apply_actions(self, strategy_actions: np.ndarray) -> None:
        for i, act in enumerate(strategy_actions):
            r = self.regions[i]
            if r["collapsed"]:
                continue
            r["action_history"].append(int(act))
            if act == 0:  # Hoard
                for res in RESOURCE_NAMES:
                    r[res] = min(RESOURCE_MAX[res], r[res] * 1.02)
                r["sustainability"] = max(0.0, r["sustainability"] - 0.02)
            elif act == 1:  # Trade - handled in _execute_learned_trades
                pass
            elif act == 2:  # Invest in growth
                prod = REGION_PRODUCTIVITY.get(i, {})
                r["food"] = min(RESOURCE_MAX["food"], r["food"] * (1.03 + 0.02 * prod.get("food", 1.0)))
                r["energy"] = min(RESOURCE_MAX["energy"], r["energy"] * (1.02 + 0.01 * prod.get("energy", 1.0)))
                r["sustainability"] += 0.01
            elif act == 3:  # Conserve
                r["sustainability"] = min(1.0, r["sustainability"] + 0.03)
            elif act == 4:  # Expand population
                r["population"] = min(POP_MAX, r["population"] * 1.04)

    # ──────────────────────────────────────────
    # Resource dynamics with interdependence
    # ──────────────────────────────────────────
    def _update_resources(self) -> None:
        for i, r in enumerate(self.regions):
            if r["collapsed"]:
                continue
            pop = r["population"]
            prod = REGION_PRODUCTIVITY.get(i, {"water": 1, "food": 1, "energy": 1, "land": 1})

            # Consumption
            conserve_mult = 0.7 if (r["action_history"] and r["action_history"][-1] == 3) else 1.0
            r["water"]  = max(0.0, r["water"]  - pop * CONSUMPTION_PER_CAPITA["water"]  * conserve_mult)
            r["food"]   = max(0.0, r["food"]   - pop * CONSUMPTION_PER_CAPITA["food"]   * conserve_mult)
            r["energy"] = max(0.0, r["energy"] - pop * CONSUMPTION_PER_CAPITA["energy"] * conserve_mult)

            # Regeneration with productivity and interdependence
            food_cap = RESOURCE_MAX["food"]
            food_bonus = 1.0
            for dep_res, weight in RESOURCE_INTERDEPENDENCE.get("food", {}).items():
                food_bonus *= (1.0 - weight + weight * r[dep_res] / RESOURCE_MAX[dep_res])
            r["food"] = min(food_cap, r["food"] + self.preset.food_regen_rate * r["food"] * (1 - r["food"] / food_cap) * prod.get("food", 1.0) * food_bonus)

            water_bonus = 1.0
            for dep_res, weight in RESOURCE_INTERDEPENDENCE.get("water", {}).items():
                water_bonus *= (1.0 - weight + weight * r[dep_res] / RESOURCE_MAX[dep_res])
            r["water"] = max(0.0, r["water"] - self.preset.water_decay_rate * r["water"] + 1.5 * prod.get("water", 1.0) * water_bonus)

            energy_bonus = 1.0
            for dep_res, weight in RESOURCE_INTERDEPENDENCE.get("energy", {}).items():
                energy_bonus *= (1.0 - weight + weight * r[dep_res] / RESOURCE_MAX[dep_res])
            r["energy"] = max(0.0, r["energy"] - self.preset.energy_decay_rate * r["energy"] + 1.0 * prod.get("energy", 1.0) * energy_bonus)

            for res in RESOURCE_NAMES:
                r[res] = float(np.clip(r[res], 0.0, RESOURCE_MAX[res]))

    # ──────────────────────────────────────────
    # Learned trade system
    # ──────────────────────────────────────────
    def _execute_learned_trades(self, actions: Dict[int, np.ndarray]) -> List[Dict[str, Any]]:
        """Execute trades based on agent-chosen targets, resources, and amounts."""
        trades: List[Dict[str, Any]] = []

        for i in range(self.num_regions):
            r = self.regions[i]
            if r["collapsed"]:
                continue
            act = actions.get(i, np.array([0, 0, 0, 0]))
            strategy = int(act[0])
            if strategy != 1:  # Only trade action triggers trade
                continue

            trade_target = int(act[1]) % self.num_regions
            trade_resource_idx = int(act[2]) % len(RESOURCE_NAMES)
            trade_amount_bucket = int(act[3]) % TRADE_AMOUNT_BUCKETS
            trade_resource = RESOURCE_NAMES[trade_resource_idx]

            # Skip self-trade
            if trade_target == i or self.regions[trade_target]["collapsed"]:
                continue

            # Check if target is a valid neighbor
            neighbors = REGION_ADJACENCY.get(i % len(REGION_ADJACENCY), [])
            if trade_target not in neighbors:
                continue

            # Calculate trade amount
            fraction = (trade_amount_bucket + 1) / TRADE_AMOUNT_BUCKETS * TRADE_MAX_FRACTION
            amount = r[trade_resource] * fraction

            if amount < 0.5:  # Minimum trade threshold
                continue

            # Trade acceptance: based on trust + utility
            trust = self.trust_matrix[trade_target, i]
            target_need = (RESOURCE_MAX[trade_resource] - self.regions[trade_target][trade_resource]) / RESOURCE_MAX[trade_resource]
            accept_prob = TRADE_ACCEPT_BASE + 0.4 * trust + 0.3 * target_need
            accept_prob = min(0.95, max(0.05, accept_prob))

            if self.np_random.random() < accept_prob:
                # Execute trade
                r[trade_resource] -= amount
                self.regions[trade_target][trade_resource] = min(
                    RESOURCE_MAX[trade_resource],
                    self.regions[trade_target][trade_resource] + amount
                )
                r["trade_balance"] += amount
                self.regions[trade_target]["trade_balance"] -= amount

                # Update trust
                self.trust_matrix[i, trade_target] = min(1.0, self.trust_matrix[i, trade_target] + TRUST_GAIN_PER_TRADE)
                self.trust_matrix[trade_target, i] = min(1.0, self.trust_matrix[trade_target, i] + TRUST_GAIN_PER_TRADE)

                # Cooperation streaks
                pair = (min(i, trade_target), max(i, trade_target))
                self.cooperation_streaks[pair] = self.cooperation_streaks.get(pair, 0) + 1

                # Track trade partners
                if trade_target not in r["trade_partners"]:
                    r["trade_partners"].append(trade_target)
                if i not in self.regions[trade_target]["trade_partners"]:
                    self.regions[trade_target]["trade_partners"].append(i)

                trades.append({
                    "from": i, "to": trade_target,
                    "resource": trade_resource,
                    "amount": round(amount, 2),
                    "trust": round(float(self.trust_matrix[i, trade_target]), 3),
                    "accepted": True,
                })
            else:
                # Trade rejected - slight trust loss (betrayal feeling)
                self.trust_matrix[i, trade_target] = max(0.0, self.trust_matrix[i, trade_target] - TRUST_LOSS_ON_BETRAYAL * 0.3)
                trades.append({
                    "from": i, "to": trade_target,
                    "resource": trade_resource,
                    "amount": round(amount, 2),
                    "trust": round(float(self.trust_matrix[i, trade_target]), 3),
                    "accepted": False,
                })

        self.trade_log.extend([t for t in trades if t["accepted"]])
        return trades

    # ──────────────────────────────────────────
    # Trust dynamics
    # ──────────────────────────────────────────
    def _decay_trust(self) -> None:
        """Natural trust decay each step."""
        mask = np.ones_like(self.trust_matrix) - np.eye(self.num_regions)
        self.trust_matrix -= TRUST_DECAY_PER_STEP * mask
        self.trust_matrix = np.clip(self.trust_matrix, 0.0, 1.0)

    def _update_alliances(self) -> None:
        """Form or break alliances based on trust threshold."""
        for i in range(self.num_regions):
            for j in range(i + 1, self.num_regions):
                pair = (i, j)
                is_allied = pair in self.alliances
                trust_level = (self.trust_matrix[i, j] + self.trust_matrix[j, i]) / 2

                if trust_level >= ALLIANCE_THRESHOLD and not is_allied:
                    self.alliances[pair] = self.current_step
                elif trust_level < ALLIANCE_THRESHOLD * 0.7 and is_allied:
                    # Alliance breaks
                    del self.alliances[pair]
                    self.betrayal_log.append({
                        "step": self.current_step,
                        "pair": list(pair),
                        "type": "alliance_break",
                        "trust": round(trust_level, 3),
                    })

    # ──────────────────────────────────────────
    # Population dynamics
    # ──────────────────────────────────────────
    def _update_population(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            avg_resource = float(np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES]))
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
            resource_health = float(np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES]))
            pop_pressure = r["population"] / POP_MAX
            target = max(0.0, min(1.0, resource_health - 0.3 * pop_pressure))
            r["sustainability"] += 0.1 * (target - r["sustainability"])
            r["sustainability"] = float(np.clip(r["sustainability"], 0.0, 1.0))

    # ──────────────────────────────────────────
    # Collapse check with root cause tracking
    # ──────────────────────────────────────────
    def _check_collapse(self) -> None:
        for r in self.regions:
            if r["collapsed"]:
                continue
            total_resources = sum(r[res] for res in RESOURCE_NAMES)
            if total_resources < 5.0:
                r["collapsed"] = True
                # Find which resource crashed first
                min_res = min(RESOURCE_NAMES, key=lambda x: r[x])
                r["collapse_cause"] = f"resource_depletion:{min_res}"
            elif r["sustainability"] < SUSTAINABILITY_COLLAPSE:
                r["collapsed"] = True
                r["collapse_cause"] = "sustainability_collapse"

    # ──────────────────────────────────────────
    # Per-region reward
    # ──────────────────────────────────────────
    def _compute_per_region_rewards(
        self, actions: Dict[int, np.ndarray], trades: List[Dict[str, Any]]
    ) -> Dict[int, float]:
        rewards: Dict[int, float] = {}
        for i, r in enumerate(self.regions):
            rw = 0.0
            if r["collapsed"]:
                rw += PENALTY_COLLAPSE
                rewards[i] = rw
                continue

            # Survival
            rw += REWARD_SURVIVAL
            # Sustainability
            rw += REWARD_SUSTAINABILITY * r["sustainability"]
            # Pop stability
            pop_ratio = r["population"] / POP_MAX
            rw += REWARD_POP_STABILITY * (1.0 - abs(pop_ratio - 0.4))
            # Overconsumption
            avg_res = float(np.mean([r[res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES]))
            if avg_res < 0.2:
                rw += PENALTY_OVERCONSUMPTION

            # Trade success bonus
            successful_trades = [t for t in trades if t["from"] == i and t.get("accepted")]
            rw += REWARD_TRADE_SUCCESS * len(successful_trades)

            # Alliance bonus
            allied_count = sum(1 for pair in self.alliances if i in pair)
            rw += REWARD_COOPERATION * 0.2 * allied_count

            rewards[i] = float(rw)
        return rewards

    # ──────────────────────────────────────────
    # Per-agent observation
    # ──────────────────────────────────────────
    def _get_agent_obs(self, region_id: int) -> np.ndarray:
        """Observation for a single agent: local + neighborhood + climate + trust."""
        r = self.regions[region_id]
        obs = []

        # Local resources (6)
        obs.append(r["water"]  / RESOURCE_MAX["water"])
        obs.append(r["food"]   / RESOURCE_MAX["food"])
        obs.append(r["energy"] / RESOURCE_MAX["energy"])
        obs.append(r["land"]   / RESOURCE_MAX["land"])
        obs.append(r["population"] / POP_MAX)
        obs.append(r["sustainability"])

        # Climate exposure (4)
        exposure = r.get("climate_exposure", {})
        obs.append(exposure.get("drought", 0.5))
        obs.append(exposure.get("flood", 0.5))
        obs.append(exposure.get("energy_crisis", 0.5))
        obs.append(exposure.get("soil_degradation", 0.5))

        # Neighbor average resources (1)
        neighbors = REGION_ADJACENCY.get(region_id % len(REGION_ADJACENCY), [])
        if neighbors:
            nb_avg = float(np.mean([
                np.mean([self.regions[nb][res] / RESOURCE_MAX[res] for res in RESOURCE_NAMES])
                for nb in neighbors if nb < self.num_regions
            ]))
        else:
            nb_avg = 0.0
        obs.append(nb_avg)

        # Climate risk (1)
        obs.append(min(1.0, self.disaster_engine.severity / 3.0))

        # Trade balance (1)
        obs.append(float(np.clip(r["trade_balance"] / 100.0, -1.0, 1.0)))

        # Trust to neighbors (3 slots, padded with 0)
        trust_vals = []
        for nb in neighbors[:3]:
            if nb < self.num_regions:
                trust_vals.append(float(self.trust_matrix[region_id, nb]))
        while len(trust_vals) < 3:
            trust_vals.append(0.0)
        obs.extend(trust_vals)

        return np.array(obs, dtype=np.float32)

    def _get_flat_obs(self) -> np.ndarray:
        """Flat observation for legacy shared mode."""
        obs = []
        for i in range(self.num_regions):
            obs.extend(self._get_agent_obs(i).tolist())
        return np.array(obs, dtype=np.float32)

    # ──────────────────────────────────────────
    # Info
    # ──────────────────────────────────────────
    def _get_info(self) -> Dict[str, Any]:
        return {
            "step": self.current_step,
            "regions": [
                {
                    "id": r["id"],
                    "water": round(float(r["water"]), 2),
                    "food": round(float(r["food"]), 2),
                    "energy": round(float(r["energy"]), 2),
                    "land": round(float(r["land"]), 2),
                    "population": round(float(r["population"]), 2),
                    "sustainability": round(float(r["sustainability"]), 3),
                    "collapsed": r["collapsed"],
                    "collapse_cause": r.get("collapse_cause"),
                    "trade_balance": round(float(r["trade_balance"]), 2),
                    "trade_partners": r.get("trade_partners", []),
                    "last_action": ACTION_NAMES[r["action_history"][-1]] if r["action_history"] else "none",
                }
                for r in self.regions
            ],
        }

    # ──────────────────────────────────────────
    # Render
    # ──────────────────────────────────────────
    def render(self) -> None:
        print(f"\n{'='*70}")
        print(f"  Step {self.current_step}")
        print(f"{'='*70}")
        for r in self.regions:
            status = "COLLAPSED" if r["collapsed"] else "active"
            allies = [p for pair in self.alliances for p in pair if r["id"] in pair and p != r["id"]]
            print(
                f"  R{r['id']} [{status}] "
                f"W:{r['water']:.1f} F:{r['food']:.1f} E:{r['energy']:.1f} "
                f"L:{r['land']:.1f} Pop:{r['population']:.0f} "
                f"Sust:{r['sustainability']:.2f} Allies:{allies}"
            )
