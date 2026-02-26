"""
Agent Earth - Flask Dashboard Server
========================================
Serves the React frontend and exposes API endpoints for
running simulations, fetching results, and updating config.
Now includes trust matrix, alliance data, and per-region rewards.
"""

from __future__ import annotations

import json
import os
import glob
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from analysis.analyzer import SimulationAnalyzer
from analysis.collapse_explainer import enrich_steps
from simulation.simulator import Simulator
from utils.config import PRESETS, WorldPreset, DEFAULT_TIMESTEPS
from utils.logger import SimulationLogger


def create_app(static_folder: str | None = None) -> Flask:
    """Factory function for the Flask application."""

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
        return jsonify({
            "presets": list(PRESETS.keys()),
            "defaults": {
                "timesteps": DEFAULT_TIMESTEPS,
                "climate_severity": 1.0,
                "num_regions": 6,
            },
            "modes": ["independent", "shared"],
        })

    @app.route("/api/run", methods=["POST"])
    def run_simulation():
        data = request.get_json(silent=True) or {}
        preset_name = data.get("preset", "default")
        timesteps = int(data.get("timesteps", DEFAULT_TIMESTEPS))
        climate_severity = float(data.get("climate_severity", 1.0))
        model_path = data.get("model_path", None)
        mode = data.get("mode", "independent")

        preset = PRESETS.get(preset_name, PRESETS["default"])
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
            mode=mode,
        )
        result = sim.run()

        analyzer = SimulationAnalyzer(sim.logger.steps, num_regions=sim.env.num_regions)
        report = analyzer.full_report()

        # Enrich steps with collapse explanations
        enriched_steps = enrich_steps(sim.logger.steps)

        return jsonify({
            "summary": result,
            "analysis": report,
            "steps": enriched_steps,
        })

    @app.route("/api/results", methods=["GET"])
    def list_results():
        results_dir = "results"
        if not os.path.exists(results_dir):
            return jsonify({"files": []})
        files = sorted(glob.glob(os.path.join(results_dir, "*.json")))
        return jsonify({"files": [os.path.basename(f) for f in files]})

    @app.route("/api/results/<filename>", methods=["GET"])
    def get_result(filename):
        path = os.path.join("results", filename)
        if not os.path.exists(path):
            return jsonify({"error": "not found"}), 404
        logger = SimulationLogger.load_json(path)
        analyzer = SimulationAnalyzer(logger.steps)
        enriched_steps = enrich_steps(logger.steps)
        return jsonify({
            "metadata": logger.metadata,
            "steps": enriched_steps,
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
        return jsonify({
            "message": "Agent Earth API is running. Build the React frontend to see the dashboard.",
            "api_docs": ["/api/config", "/api/run (POST)", "/api/results"],
        }), 200

    return app
