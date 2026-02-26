"""
Agent Earth — Main Entry Point
=================================
CLI for training, simulating, analysing, and launching the dashboard.

Usage
-----
    python main.py train   [--timesteps N] [--preset NAME]
    python main.py simulate [--timesteps N] [--preset NAME] [--model PATH] [--output DIR]
    python main.py analyse  [--input PATH]
    python main.py dashboard [--port PORT]
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List

from utils.config import PRESETS, TRAIN_TIMESTEPS, DEFAULT_TIMESTEPS


def cmd_train(args: argparse.Namespace) -> None:
    """Train the shared PPO agent."""
    from env.world_env import WorldEnv
    from agents.shared_agent import SharedAgent

    preset = PRESETS.get(args.preset, PRESETS["default"])
    env = WorldEnv(preset=preset, max_steps=args.timesteps, climate_severity=preset.climate_severity)
    agent = SharedAgent(env)
    agent.train(total_timesteps=args.train_steps)
    agent.save(args.model)


def cmd_simulate(args: argparse.Namespace) -> None:
    """Run a simulation episode."""
    from simulation.simulator import Simulator

    preset = PRESETS.get(args.preset, PRESETS["default"])
    sim = Simulator(
        preset=preset,
        max_steps=args.timesteps,
        model_path=args.model if args.model != "none" else None,
        output_dir=args.output,
        climate_severity=preset.climate_severity,
    )
    result = sim.run(render=args.render)
    print(f"\n  Summary: {json.dumps(result, indent=2)}")


def cmd_analyse(args: argparse.Namespace) -> None:
    """Run post-simulation analysis on saved results."""
    from analysis.analyzer import SimulationAnalyzer
    from utils.logger import SimulationLogger

    logger = SimulationLogger.load_json(args.input)
    analyzer = SimulationAnalyzer(logger.steps)
    report = analyzer.full_report()

    print("\n" + "=" * 60)
    print("  Agent Earth — Analysis Report")
    print("=" * 60)
    for key, value in report.items():
        print(f"\n  {key}:")
        if isinstance(value, dict):
            for k, v in value.items():
                print(f"    {k}: {v}")
        else:
            print(f"    {value}")

    # Save insights
    logger.save_insights(
        {k: str(v) for k, v in report.items()},
        filename="analysis_insights.txt",
    )
    print(f"\n  Insights saved → {args.input.rsplit('.', 1)[0]}_insights.txt")


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Launch the Flask + React dashboard."""
    from dashboard.app import create_app
    app = create_app()
    print(f"\n  Starting Agent Earth Dashboard on http://localhost:{args.port}")
    app.run(host="0.0.0.0", port=args.port, debug=True)


def main(argv: List[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="agent_earth",
        description="Agent Earth: Adaptive Multi-Agent Resource Scarcity Simulator",
    )
    sub = parser.add_subparsers(dest="command")

    # ── train ─────────────────────────────────
    p_train = sub.add_parser("train", help="Train the RL agent")
    p_train.add_argument("--timesteps", type=int, default=500, help="Max env steps per episode")
    p_train.add_argument("--train-steps", type=int, default=TRAIN_TIMESTEPS, help="Total PPO training steps")
    p_train.add_argument("--preset", type=str, default="default", choices=PRESETS.keys())
    p_train.add_argument("--model", type=str, default="models/agent_earth_ppo", help="Save path")

    # ── simulate ──────────────────────────────
    p_sim = sub.add_parser("simulate", help="Run a simulation episode")
    p_sim.add_argument("--timesteps", type=int, default=DEFAULT_TIMESTEPS)
    p_sim.add_argument("--preset", type=str, default="default", choices=PRESETS.keys())
    p_sim.add_argument("--model", type=str, default="none", help="Model path (or 'none' for random)")
    p_sim.add_argument("--output", type=str, default="results")
    p_sim.add_argument("--render", action="store_true")

    # ── analyse ───────────────────────────────
    p_ana = sub.add_parser("analyse", help="Analyse a saved run")
    p_ana.add_argument("--input", type=str, required=True, help="Path to run JSON")

    # ── dashboard ─────────────────────────────
    p_dash = sub.add_parser("dashboard", help="Launch the web dashboard")
    p_dash.add_argument("--port", type=int, default=5000)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"train": cmd_train, "simulate": cmd_simulate, "analyse": cmd_analyse, "dashboard": cmd_dashboard}[args.command](args)


if __name__ == "__main__":
    main()
