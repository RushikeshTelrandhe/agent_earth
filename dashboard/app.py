"""
Agent Earth - Flask Dashboard Server
========================================
Serves the React frontend and exposes API endpoints for
running simulations, fetching results, and updating config.
Now includes trust matrix, alliance data, and per-region rewards.
"""

from __future__ import annotations

import json
import logging
import os
import glob
import traceback
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from analysis.analyzer import SimulationAnalyzer
from analysis.collapse_explainer import enrich_steps
from analysis.rl_advisor import generate_response as advisor_respond
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
    # ── CORS (environment-based whitelist) ────
    allowed_origins = os.environ.get("ALLOWED_ORIGINS", "*")
    if allowed_origins == "*":
        CORS(app)
    else:
        origins = [o.strip() for o in allowed_origins.split(",") if o.strip()]
        CORS(app, origins=origins)

    # ── Logging ────
    is_production = os.environ.get("FLASK_ENV", "production") == "production"
    logging.basicConfig(
        level=logging.INFO if is_production else logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("agent_earth")

    # Register crowdsense pilot layer
    from crowdsense.routes import crowdsense_bp
    app.register_blueprint(crowdsense_bp)

    # ── Health Check ──────────────────────────────
    @app.route("/health")
    def health_check():
        return jsonify({"status": "ok", "service": "agent-earth-api"})

    # ── Global Error Handler ─────────────────────
    @app.errorhandler(Exception)
    def handle_exception(e):
        logger.error(f"Unhandled exception: {e}")
        if not is_production:
            return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
        return jsonify({"error": "Internal server error"}), 500

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
    @app.route("/api/advisor", methods=["POST"])
    def advisor():
        data = request.get_json(silent=True) or {}
        question = data.get("question", "Give me an overview")
        sim_steps = data.get("steps", [])
        sim_analysis = data.get("analysis", {})

        result = advisor_respond(question, sim_steps, sim_analysis)
        return jsonify(result)

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
