"""
Agent Earth — Shared RL Agent
================================
Thin wrapper around Stable-Baselines3 PPO.
One shared policy controls all regions; behaviour diverges
because each region receives its own state slice.
"""

from __future__ import annotations

import os
from typing import Optional

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from env.world_env import WorldEnv
from utils.config import TRAIN_TIMESTEPS


class _ProgressCallback(BaseCallback):
    """Simple training progress printer."""

    def __init__(self, print_freq: int = 5000, verbose: int = 0) -> None:
        super().__init__(verbose)
        self.print_freq = print_freq

    def _on_step(self) -> bool:
        if self.n_calls % self.print_freq == 0:
            mean_reward = 0.0
            if len(self.model.ep_info_buffer) > 0:
                mean_reward = sum(ep["r"] for ep in self.model.ep_info_buffer) / len(self.model.ep_info_buffer)
            print(f"  [Step {self.n_calls:>7}]  mean_reward = {mean_reward:.2f}")
        return True


class SharedAgent:
    """Parameter-shared multi-agent RL wrapper using PPO.

    Parameters
    ----------
    env : WorldEnv
        The gymnasium environment.
    model_path : str | None
        If provided, load a pretrained model.
    lr : float
        Learning rate for PPO.
    """

    def __init__(
        self,
        env: WorldEnv,
        model_path: Optional[str] = None,
        lr: float = 3e-4,
    ) -> None:
        self.env = env
        if model_path and os.path.exists(model_path):
            print(f"  Loading model from {model_path}")
            self.model = PPO.load(model_path, env=env)
        else:
            self.model = PPO(
                "MlpPolicy",
                env,
                learning_rate=lr,
                n_steps=2048,
                batch_size=64,
                n_epochs=10,
                gamma=0.99,
                gae_lambda=0.95,
                clip_range=0.2,
                verbose=0,
            )

    def train(self, total_timesteps: int = TRAIN_TIMESTEPS) -> None:
        """Train the shared policy."""
        print(f"\n{'='*50}")
        print(f"  Training PPO for {total_timesteps:,} steps …")
        print(f"{'='*50}\n")
        callback = _ProgressCallback(print_freq=max(1000, total_timesteps // 20))
        self.model.learn(total_timesteps=total_timesteps, callback=callback)
        print("\n  Training complete.\n")

    def predict(self, obs, deterministic: bool = True):
        """Get action from the shared policy."""
        action, _states = self.model.predict(obs, deterministic=deterministic)
        return action

    def save(self, path: str = "models/agent_earth_ppo") -> str:
        """Save model weights to disk."""
        os.makedirs(os.path.dirname(path) or "models", exist_ok=True)
        self.model.save(path)
        print(f"  Model saved → {path}")
        return path

    def load(self, path: str) -> None:
        """Load model weights from disk."""
        self.model = PPO.load(path, env=self.env)
        print(f"  Model loaded ← {path}")
