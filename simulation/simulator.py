"""
Agent Earth - Simulation Runner
==================================
Orchestrates the environment, agents, and logger for a full
simulation run. Supports both shared and independent agent modes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from env.world_env import WorldEnv
from utils.config import DEFAULT_TIMESTEPS, PRESETS, WorldPreset, NUM_ACTIONS, RESOURCE_NAMES, TRADE_AMOUNT_BUCKETS
from utils.logger import SimulationLogger


class Simulator:
    """End-to-end simulation runner.

    Parameters
    ----------
    preset : WorldPreset | None
        World configuration preset.
    max_steps : int
        Number of timesteps per episode.
    model_path : str | None
        Path to a pretrained PPO model (shared mode) or model directory (independent mode).
    output_dir : str
        Directory for result files.
    climate_severity : float
        Override climate severity (1.0 = default).
    mode : str
        "independent" for multi-agent, "shared" for legacy single-policy.
    """

    def __init__(
        self,
        preset: Optional[WorldPreset] = None,
        max_steps: int = DEFAULT_TIMESTEPS,
        model_path: Optional[str] = None,
        output_dir: str = "results",
        climate_severity: float = 1.0,
        mode: str = "independent",
    ) -> None:
        self.preset = preset or PRESETS["default"]
        self.max_steps = max_steps
        self.output_dir = output_dir
        self.mode = mode

        # Build environment
        self.env = WorldEnv(
            preset=self.preset,
            max_steps=max_steps,
            climate_severity=climate_severity,
        )

        # Build or load agents
        self.agent = None
        self.model_path = model_path

        if mode == "independent":
            from agents.independent_agents import IndependentAgentManager
            self.agent = IndependentAgentManager(self.env, num_regions=self.env.num_regions)
            if model_path:
                self.agent.load(model_path)
        elif mode == "shared" and model_path:
            from agents.shared_agent import SharedAgent
            self.agent = SharedAgent(self.env, model_path=model_path)

        # Logger
        self.logger = SimulationLogger(output_dir=output_dir)

    def run(self, render: bool = False) -> Dict[str, Any]:
        """Execute one full simulation episode.

        Returns
        -------
        dict with keys: metadata, steps, json_path, csv_path
        """
        self.logger.clear()
        self.logger.set_metadata(
            preset=self.preset.name,
            max_steps=self.max_steps,
            climate_severity=self.env.climate_severity,
            num_regions=self.env.num_regions,
            mode=self.mode,
        )

        obs, info = self.env.reset()
        self.logger.log_step(0, info)

        total_reward = 0.0
        done = False
        step = 0

        while not done:
            if self.mode == "independent" and self.agent is not None:
                # Multi-agent: get per-agent observations and actions
                agent_obs = {i: self.env._get_agent_obs(i) for i in range(self.env.num_regions)}
                actions = self.agent.predict(agent_obs)
                obs_dict, rewards_dict, terminated, truncated, info = self.env.step_multi(actions)
                reward = sum(rewards_dict.values())
                done = terminated or truncated
            elif self.mode == "shared" and self.agent is not None:
                action = self.agent.predict(obs)
                obs, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated
            else:
                # Random actions
                if self.mode == "independent":
                    actions = {
                        i: np.array([
                            self.env.np_random.integers(NUM_ACTIONS),
                            self.env.np_random.integers(self.env.num_regions),
                            self.env.np_random.integers(len(RESOURCE_NAMES)),
                            self.env.np_random.integers(TRADE_AMOUNT_BUCKETS),
                        ]) for i in range(self.env.num_regions)
                    }
                    obs_dict, rewards_dict, terminated, truncated, info = self.env.step_multi(actions)
                    reward = sum(rewards_dict.values())
                else:
                    action = self.env.action_space.sample()
                    obs, reward, terminated, truncated, info = self.env.step(action)
                done = terminated or truncated

            total_reward += reward
            step += 1

            # Enrich info with per-region rewards and trust
            if self.mode == "independent":
                info["per_region_rewards"] = self.env.per_region_rewards

            self.logger.log_step(step, info)

            if render:
                self.env.render()

        # Persist
        json_path = self.logger.save_json()
        csv_path = self.logger.save_csv()

        summary = {
            "total_reward": round(total_reward, 2),
            "steps_completed": step,
            "json_path": json_path,
            "csv_path": csv_path,
        }
        print(f"\n  Simulation complete - {step} steps, reward={total_reward:.2f}")
        print(f"  Results -> {json_path}")
        return summary
