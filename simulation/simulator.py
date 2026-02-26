"""
Agent Earth — Simulation Runner
==================================
Orchestrates the environment, agent, and logger for a full
simulation run (either with a trained policy or random actions).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from agents.shared_agent import SharedAgent
from env.world_env import WorldEnv
from utils.config import DEFAULT_TIMESTEPS, PRESETS, WorldPreset
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
        Path to a pretrained PPO model.  If ``None`` uses random actions.
    output_dir : str
        Directory for result files.
    climate_severity : float
        Override climate severity (1.0 = default).
    """

    def __init__(
        self,
        preset: Optional[WorldPreset] = None,
        max_steps: int = DEFAULT_TIMESTEPS,
        model_path: Optional[str] = None,
        output_dir: str = "results",
        climate_severity: float = 1.0,
    ) -> None:
        self.preset = preset or PRESETS["default"]
        self.max_steps = max_steps
        self.output_dir = output_dir

        # Build environment
        self.env = WorldEnv(
            preset=self.preset,
            max_steps=max_steps,
            climate_severity=climate_severity,
        )

        # Build or load agent
        self.agent: Optional[SharedAgent] = None
        self.model_path = model_path
        if model_path:
            self.agent = SharedAgent(self.env, model_path=model_path)

        # Logger
        self.logger = SimulationLogger(output_dir=output_dir)

    def run(self, render: bool = False) -> Dict[str, Any]:
        """Execute one full simulation episode.

        Returns
        -------
        dict with keys: metadata, steps (list), json_path, csv_path
        """
        self.logger.clear()
        self.logger.set_metadata(
            preset=self.preset.name,
            max_steps=self.max_steps,
            climate_severity=self.env.climate_severity,
            num_regions=self.env.num_regions,
        )

        obs, info = self.env.reset()
        self.logger.log_step(0, info)

        total_reward = 0.0
        done = False
        step = 0

        while not done:
            # Choose action
            if self.agent:
                action = self.agent.predict(obs)
            else:
                action = self.env.action_space.sample()

            obs, reward, terminated, truncated, info = self.env.step(action)
            done = terminated or truncated
            total_reward += reward
            step += 1

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
