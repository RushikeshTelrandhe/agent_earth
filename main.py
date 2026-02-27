"""
Agent Earth - Main Entry Point
==================================
CLI: train, simulate, analyse, dashboard
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from utils.config import PRESETS, WorldPreset, DEFAULT_TIMESTEPS, TRAIN_TIMESTEPS, DEMO_TRAIN_TIMESTEPS


def cmd_train(args: argparse.Namespace) -> None:
    """Train RL agents."""
    preset = PRESETS.get(args.preset, PRESETS["default"])

    if args.mode == "independent":
        from env.world_env import WorldEnv
        from agents.independent_agents import IndependentAgentManager
        env = WorldEnv(preset=preset, max_steps=args.timesteps, climate_severity=preset.climate_severity)
        manager = IndependentAgentManager(env, num_regions=env.num_regions, lr=3e-4)
        manager.train(total_timesteps=args.train_steps)
        manager.save("models")
    else:
        from env.world_env import WorldEnv
        from agents.shared_agent import SharedAgent
        env = WorldEnv(preset=preset, max_steps=args.timesteps, climate_severity=preset.climate_severity)
        agent = SharedAgent(env, lr=3e-4)
        agent.train(total_timesteps=args.train_steps)
        agent.save("models/agent_earth_ppo")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Run simulation."""
    from simulation.simulator import Simulator
    preset = PRESETS.get(args.preset, PRESETS["default"])
    sim = Simulator(
        preset=preset,
        max_steps=args.timesteps,
        model_path=args.model,
        output_dir=args.output,
        climate_severity=preset.climate_severity,
        mode=args.mode,
    )
    result = sim.run(render=args.render)
    print(f"\n  Summary: {json.dumps(result, indent=2)}")


def cmd_analyse(args: argparse.Namespace) -> None:
    """Run post-simulation analysis."""
    from analysis.analyzer import SimulationAnalyzer
    from utils.logger import SimulationLogger

    logger = SimulationLogger.load_json(args.input)
    num_regions = logger.metadata.get("num_regions", 6)
    analyzer = SimulationAnalyzer(logger.steps, num_regions=num_regions)
    report = analyzer.full_report()

    print("\n" + "=" * 60)
    print("  Agent Earth - Analysis Report")
    print("=" * 60)
    for key, value in report.items():
        print(f"\n  {key}:")
        if isinstance(value, dict):
            for k, v in value.items():
                print(f"    {k}: {v}")
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            for item in value:
                print(f"    {item}")
        else:
            print(f"    {value}")

    # Save insights
    logger.save_insights(
        {k: str(v) for k, v in report.items()},
        filename="analysis_insights.txt",
    )
    print(f"\n  Insights saved -> {args.input.rsplit('.', 1)[0]}_insights.txt")


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Launch the Flask dashboard."""
    from dashboard.app import create_app

    port = int(os.environ.get("PORT", args.port))
    debug = os.environ.get("FLASK_ENV", "development") != "production"
    app = create_app()
    print(f"\n  Starting Agent Earth Dashboard on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=debug)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agent Earth - Adaptive Multi-Agent Resource Scarcity Simulator"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── train ──
    p_train = sub.add_parser("train", help="Train RL agents")
    p_train.add_argument("--train-steps", type=int, default=TRAIN_TIMESTEPS)
    p_train.add_argument("--timesteps", type=int, default=DEFAULT_TIMESTEPS, help="Episode length")
    p_train.add_argument("--preset", type=str, default="default", choices=list(PRESETS.keys()))
    p_train.add_argument("--mode", type=str, default="independent", choices=["independent", "shared"])
    p_train.add_argument("--demo", action="store_true", help="Fast demo training (5k steps)")

    # ── simulate ──
    p_sim = sub.add_parser("simulate", help="Run simulation")
    p_sim.add_argument("--timesteps", type=int, default=DEFAULT_TIMESTEPS)
    p_sim.add_argument("--model", type=str, default=None, help="Model path (shared) or directory (independent)")
    p_sim.add_argument("--output", type=str, default="results")
    p_sim.add_argument("--preset", type=str, default="default", choices=list(PRESETS.keys()))
    p_sim.add_argument("--render", action="store_true")
    p_sim.add_argument("--mode", type=str, default="independent", choices=["independent", "shared"])

    # ── analyse ──
    p_analyse = sub.add_parser("analyse", help="Analyse saved run")
    p_analyse.add_argument("--input", type=str, required=True)

    # ── dashboard ──
    p_dash = sub.add_parser("dashboard", help="Launch dashboard")
    p_dash.add_argument("--port", type=int, default=5000)

    args = parser.parse_args()

    # Demo mode override
    if hasattr(args, "demo") and args.demo:
        args.train_steps = DEMO_TRAIN_TIMESTEPS

    {"train": cmd_train, "simulate": cmd_simulate, "analyse": cmd_analyse, "dashboard": cmd_dashboard}[args.command](args)


if __name__ == "__main__":
    main()
