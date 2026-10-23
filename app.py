"""
Celebrio AI Planner - Flask Application Server
Serves the GenAI Celebration Planning Dashboard & REST APIs.
"""

import os
import json
import logging
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

from models import PERSONA_DEFAULTS, validate_event_input
from planner_engine import PlannerEngine

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CelebrioApp")

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Max 2MB payload guard

# Initialize the Planner Engine
engine = PlannerEngine(api_key=os.getenv("GEMINI_API_KEY"))


@app.route("/")
def serve_index():
    """Serves the main application dashboard."""
    return send_from_directory(app.static_folder, "index.html")


@app.route("/health", methods=["GET"])
def health():
    """System health check and GenAI status."""
    return jsonify({
        "status": "healthy",
        "service": "Celebrio AI Celebration & Event Planner",
        "version": "1.0.0",
        "genai_active": engine.is_genai_enabled()
    }), 200


@app.route("/api/presets", methods=["GET"])
def get_presets():
    """Returns supported celebration personas and initial configuration templates."""
    return jsonify({
        "success": True,
        "personas": PERSONA_DEFAULTS
    }), 200


@app.route("/api/validate", methods=["POST"])
def validate_payload():
    """
    Validates input parameters without running full generation.
    Useful for live interactive testing and edge-case demonstration.
    """
    try:
        data = request.get_json(force=True, silent=False)
        validated = validate_event_input(data)
        return jsonify({
            "success": True,
            "message": "Payload is valid.",
            "data": validated
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error(f"Validation error: {e}")
        return jsonify({"success": False, "error": "Invalid request body."}), 400


@app.route("/api/generate-plan", methods=["POST"])
def generate_plan():
    """
    Primary endpoint: Synthesizes budgets, countdown timelines,
    vendor checklists, and personalized creative ideas based on user context.
    """
    try:
        data = request.get_json(force=True)
        plan = engine.generate_full_plan(data)
        return jsonify({
            "success": True,
            "plan": plan
        }), 200
    except ValueError as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Plan generation error")
        return jsonify({"success": False, "error": "Failed to synthesize event plan. Please check inputs."}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Interactive conversational assistant for contextual guidance,
    budget modifications, legal permits, and creative problem solving.
    """
    try:
        data = request.get_json(force=True)
        message = str(data.get("message", "")).strip()
        if not message:
            return jsonify({"success": False, "error": "Message cannot be empty."}), 400

        event_context = data.get("event_context", {})
        reply = engine.chat(message, event_context)
        return jsonify({
            "success": True,
            "reply": reply
        }), 200
    except Exception as e:
        logger.exception("Chat endpoint error")
        return jsonify({"success": False, "error": "Assistant temporarily unavailable."}), 500


@app.route("/api/vendor-inquiry", methods=["POST"])
def vendor_inquiry():
    """Generates customized RFP / quote inquiry email for vendors."""
    try:
        data = request.get_json(force=True)
        vendor_category = str(data.get("vendor_category", "Venue")).strip()
        event_context = data.get("event_context", {})
        
        email_body = engine.generate_vendor_inquiry(vendor_category, event_context)
        return jsonify({
            "success": True,
            "vendor_category": vendor_category,
            "inquiry_email": email_body
        }), 200
    except Exception as e:
        logger.exception("Vendor inquiry error")
        return jsonify({"success": False, "error": "Failed to generate vendor inquiry."}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    print(f"Starting Celebrio AI Planner on http://localhost:{port} (GenAI active: {engine.is_genai_enabled()})")
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
