"""
Agent Earth - Independent Multi-Agent Manager
===============================================
Manages N independent PPO models, one per region.
CTDE-lite: agents train with partial global info, act with local observations.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import numpy as np
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from env.world_env import WorldEnv
from env.multi_agent_env import SingleAgentView, CoordinatedMultiAgentEnv
from utils.config import NUM_REGIONS, TRAIN_TIMESTEPS, NUM_ACTIONS, RESOURCE_NAMES, TRADE_AMOUNT_BUCKETS


class _RegionProgressCallback(BaseCallback):
    """Training progress printer for a single region."""

    def __init__(self, region_id: int, print_freq: int = 2000, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.region_id = region_id
        self.print_freq = print_freq

    def _on_step(self) -> bool:
        if self.n_calls % self.print_freq == 0:
            mean_reward = 0.0
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = sum(ep["r"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            print(f"    Region {self.region_id} [Step {self.n_calls:>6}]  mean_reward = {mean_reward:.2f}")
        return True


class IndependentAgentManager:
    """Manages independent PPO agents, one per region.

    Parameters
    ----------
    env : WorldEnv
        The shared world environment.
    num_regions : int
        Number of agents/regions.
    lr : float
        Learning rate for all PPO models.
    """

    def __init__(
        self,
        env: WorldEnv,
        num_regions: int = NUM_REGIONS,
        lr: float = 3e-4,
    ) -> None:
        self.env = env
        self.num_regions = num_regions
        self.models: Dict[int, PPO] = {}
        self.agent_envs: Dict[int, SingleAgentView] = {}

        # Create per-agent environments and models
        for i in range(num_regions):
            agent_env = SingleAgentView(i, env)
            self.agent_envs[i] = agent_env
            self.models[i] = PPO(
                "MlpPolicy",
                agent_env,
                learning_rate=lr,
                n_steps=512,
                batch_size=64,
                n_epochs=5,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                verbose=0,
            )

    def train(self, total_timesteps: int = TRAIN_TIMESTEPS) -> None:
        """Train all agents in round-robin fashion.

        Each agent trains for total_timesteps // num_regions steps per round,
        while other agents use their current policies.
        """
        per_agent_steps = max(500, total_timesteps // self.num_regions)

        print(f"\n{'='*60}")
        print(f"  Training {self.num_regions} independent agents")
        print(f"  {per_agent_steps:,} steps per agent ({total_timesteps:,} total)")
        print(f"{'='*60}\n")

        for i in range(self.num_regions):
            print(f"  -- Region {i} --")
            callback = _RegionProgressCallback(
                region_id=i,
                print_freq=max(500, per_agent_steps // 10),
            )
            self.models[i].learn(
                total_timesteps=per_agent_steps,
                callback=callback,
                reset_num_timesteps=False,
            )
            print()

        print("  Training complete.\n")

    def predict(self, observations: Dict[int, np.ndarray], deterministic: bool = True) -> Dict[int, np.ndarray]:
        """Get actions from all independent agents."""
        actions = {}
        for i in range(self.num_regions):
            obs = observations.get(i, self.env._get_agent_obs(i))
            action, _ = self.models[i].predict(obs, deterministic=deterministic)
            actions[i] = action
        return actions

    def predict_single(self, region_id: int, obs: np.ndarray, deterministic: bool = True) -> np.ndarray:
        """Get action from a single agent."""
        action, _ = self.models[region_id].predict(obs, deterministic=deterministic)
        return action

    def save(self, directory: str = "models") -> List[str]:
        """Save all models to individual files."""
        os.makedirs(directory, exist_ok=True)
        paths = []
        for i in range(self.num_regions):
            path = os.path.join(directory, f"region_{i}")
            self.models[i].save(path)
            paths.append(path)
        print(f"  Models saved -> {directory}/region_{{0..{self.num_regions-1}}}.zip")
        return paths

    def load(self, directory: str = "models") -> None:
        """Load all models from individual files."""
        for i in range(self.num_regions):
            path = os.path.join(directory, f"region_{i}")
            if os.path.exists(path + ".zip"):
                self.models[i] = PPO.load(path, env=self.agent_envs[i])
        print(f"  Models loaded <- {directory}/region_{{0..{self.num_regions-1}}}.zip")
