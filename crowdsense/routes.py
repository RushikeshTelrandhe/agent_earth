"""
Crowdsense Flask Routes
========================
Blueprint with auth, detection ingestion, and signal endpoints.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, request
from crowdsense.auth import signup, login, require_auth, REGIONS
from crowdsense.store import add_detection, get_region_signals, get_all_region_signals, get_stats
from crowdsense.adapter import get_all_modifiers

crowdsense_bp = Blueprint("crowdsense", __name__, url_prefix="/api/crowdsense")


@crowdsense_bp.route("/signup", methods=["POST"])
def route_signup():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")
    region_id = int(data.get("region_id", 0))

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required"}), 400

    result = signup(name, email, password, region_id)
    if "error" in result:
        return jsonify(result), 400
    return jsonify(result)


@crowdsense_bp.route("/login", methods=["POST"])
def route_login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    result = login(email, password)
    if "error" in result:
        return jsonify(result), 401
    return jsonify(result)


@crowdsense_bp.route("/detections", methods=["POST"])
@require_auth
def route_detections():
    data = request.get_json(silent=True) or {}
    user_payload = request.user  # type: ignore

    detected_objects = data.get("detected_objects", [])
    frame_count = int(data.get("frame_object_count", len(detected_objects)))

    result = add_detection(
        user_id=user_payload["user_id"],
        region_id=user_payload["region_id"],
        detected_objects=detected_objects,
        frame_object_count=frame_count,
    )
    return jsonify(result)


@crowdsense_bp.route("/region-signals/<int:region_id>", methods=["GET"])
def route_region_signals(region_id):
    if region_id not in REGIONS:
        return jsonify({"error": "Invalid region"}), 400
    return jsonify(get_region_signals(region_id))


@crowdsense_bp.route("/all-signals", methods=["GET"])
def route_all_signals():
    return jsonify({
        "regions": get_all_region_signals(),
        "modifiers": get_all_modifiers(),
    })


@crowdsense_bp.route("/status", methods=["GET"])
def route_status():
    return jsonify({
        "status": "operational",
        "mode": "pilot",
        "regions": REGIONS,
        "stats": get_stats(),
    })
