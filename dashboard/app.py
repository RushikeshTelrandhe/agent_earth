"""
Agent Earth — Flask Dashboard Server
========================================
Serves the React frontend and exposes API endpoints for
running simulations, fetching results, and updating config.
"""

from __future__ import annotations

import json
import os
import glob
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from analysis.analyzer import SimulationAnalyzer
from simulation.simulator import Simulator
from utils.config import PRESETS, WorldPreset, DEFAULT_TIMESTEPS
from utils.logger import SimulationLogger


def create_app(static_folder: str | None = None) -> Flask:
    """Factory function for the Flask application."""

    # Resolve static folder to the React build directory
    if static_folder is None:
        static_folder = os.path.join(os.path.dirname(__file__), "frontend", "dist")

    app = Flask(
        __name__,
        static_folder=static_folder,
        static_url_path="",
    )
    CORS(app)

    # ── API Routes ─────────────────────────────

    @app.route("/api/config", methods=["GET"])
    def get_config():
        """Return available presets and defaults."""
        return jsonify({
            "presets": list(PRESETS.keys()),
            "defaults": {
                "timesteps": DEFAULT_TIMESTEPS,
                "climate_severity": 1.0,
                "num_regions": 6,
            }
        })

    @app.route("/api/run", methods=["POST"])
    def run_simulation():
        """Run a simulation and return results + analysis."""
        data = request.get_json(silent=True) or {}
        preset_name = data.get("preset", "default")
        timesteps = int(data.get("timesteps", DEFAULT_TIMESTEPS))
        climate_severity = float(data.get("climate_severity", 1.0))
        model_path = data.get("model_path", None)

        preset = PRESETS.get(preset_name, PRESETS["default"])
        # Override climate severity from slider
        preset_copy = WorldPreset(
            name=preset.name,
            water_init=preset.water_init,
            food_init=preset.food_init,
            energy_init=preset.energy_init,
            land_init=preset.land_init,
            pop_init=preset.pop_init,
            climate_severity=climate_severity,
            food_regen_rate=preset.food_regen_rate,
            water_decay_rate=preset.water_decay_rate,
            energy_decay_rate=preset.energy_decay_rate,
        )

        sim = Simulator(
            preset=preset_copy,
            max_steps=timesteps,
            model_path=model_path,
            output_dir="results",
            climate_severity=climate_severity,
        )
        result = sim.run()

        # Analysis
        analyzer = SimulationAnalyzer(sim.logger.steps, num_regions=sim.env.num_regions)
        report = analyzer.full_report()

        return jsonify({
            "summary": result,
            "analysis": report,
            "steps": sim.logger.steps,
        })

    @app.route("/api/results", methods=["GET"])
    def list_results():
        """List available saved simulation results."""
        results_dir = "results"
        if not os.path.exists(results_dir):
            return jsonify({"files": []})
        files = sorted(glob.glob(os.path.join(results_dir, "*.json")))
        return jsonify({"files": [os.path.basename(f) for f in files]})

    @app.route("/api/results/<filename>", methods=["GET"])
    def get_result(filename):
        """Load and return a saved simulation run."""
        path = os.path.join("results", filename)
        if not os.path.exists(path):
            return jsonify({"error": "not found"}), 404
        logger = SimulationLogger.load_json(path)
        analyzer = SimulationAnalyzer(logger.steps)
        return jsonify({
            "metadata": logger.metadata,
            "steps": logger.steps,
            "analysis": analyzer.full_report(),
        })

    # ── Serve React SPA ────────────────────────
    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def serve_spa(path):
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        index_path = os.path.join(app.static_folder, "index.html")
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, "index.html")
        return jsonify({"message": "Agent Earth API is running. Build the React frontend to see the dashboard.", "api_docs": ["/api/config", "/api/run (POST)", "/api/results"]}), 200

    return app
