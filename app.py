"""
Celebrio AI Planner - Production Flask Application Server.
Serves the GenAI Celebration Planning Dashboard & REST APIs with high-efficiency
caching, Gzip compression, and structured error handlers.
"""

import os
import json
import gzip
import logging
from typing import Any, Tuple
from flask import Flask, request, jsonify, send_from_directory, Response, make_response
from dotenv import load_dotenv

from models import PERSONA_DEFAULTS, validate_event_input, CelebrioValidationError
from planner_engine import PlannerEngine

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("CelebrioApp")

app = Flask(__name__, static_folder="static", static_url_path="")
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Max 2MB payload guard
app.config["JSON_SORT_KEYS"] = False

# Initialize the Planner Engine with memory caching
engine = PlannerEngine(api_key=os.getenv("GEMINI_API_KEY"))

# Pre-serialized presets JSON with ETag for instant 0ms responses
_PRESETS_JSON: str = json.dumps({"success": True, "personas": PERSONA_DEFAULTS})
_PRESETS_ETAG: str = '"celebrio-presets-v1"'


@app.after_request
def add_performance_and_security_headers(response: Response) -> Response:
    """
    Applies security headers and Gzip compression to responses over 1KB.

    Args:
        response: Outgoing Flask Response object.

    Returns:
        Augmented Response with security headers and optional Gzip stream.
    """
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"

    accept_encoding = request.headers.get("Accept-Encoding", "")
    compressible_types = (
        "application/json", "text/html", "text/css", "application/javascript"
    )
    if (
        "gzip" in accept_encoding.lower() and
        response.status_code == 200 and
        response.content_length and response.content_length > 1024 and
        response.mimetype in compressible_types
    ):
        try:
            compressed = gzip.compress(response.get_data())
            response.set_data(compressed)
            response.headers["Content-Encoding"] = "gzip"
            response.headers["Content-Length"] = len(compressed)
        except Exception:
            pass

    return response


# -------------------------------------------------------------
# Global Error Handlers (Code Quality & Security)
# -------------------------------------------------------------
@app.errorhandler(400)
def handle_bad_request(e: Any) -> Tuple[Response, int]:
    """Catches HTTP 400 Bad Request errors and formats standard JSON."""
    return jsonify({
        "success": False,
        "error": "Bad request format or invalid parameters.",
        "status": 400
    }), 400


@app.errorhandler(404)
def handle_not_found(e: Any) -> Tuple[Response, int]:
    """Catches HTTP 404 Not Found errors and formats standard JSON."""
    return jsonify({
        "success": False,
        "error": "Requested resource was not found.",
        "status": 404
    }), 404


@app.errorhandler(405)
def handle_method_not_allowed(e: Any) -> Tuple[Response, int]:
    """Catches HTTP 405 Method Not Allowed errors and formats standard JSON."""
    return jsonify({
        "success": False,
        "error": "HTTP method not allowed for this endpoint.",
        "status": 405
    }), 405


@app.errorhandler(413)
def handle_payload_too_large(e: Any) -> Tuple[Response, int]:
    """Catches HTTP 413 Payload Too Large errors when payload exceeds 2MB."""
    return jsonify({
        "success": False,
        "error": "Payload exceeds maximum allowed 2MB limit.",
        "status": 413
    }), 413


@app.errorhandler(500)
def handle_internal_server_error(e: Any) -> Tuple[Response, int]:
    """Catches unhandled server exceptions and returns generic error response."""
    logger.exception("Unhandled server exception: %s", e)
    return jsonify({
        "success": False,
        "error": "An internal error occurred. Please try again.",
        "status": 500
    }), 500


# -------------------------------------------------------------
# Web Application & API Routes
# -------------------------------------------------------------
@app.route("/")
def serve_index() -> Response:
    """Serves the main application dashboard with short cache-control."""
    response = make_response(send_from_directory(app.static_folder, "index.html"))
    response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.route("/static/<path:filename>")
def serve_static(filename: str) -> Response:
    """Serves static assets with long-term browser caching for high efficiency."""
    response = make_response(send_from_directory(app.static_folder, filename))
    response.headers["Cache-Control"] = "public, max-age=86400"
    return response


@app.route("/health", methods=["GET"])
def health() -> Tuple[Response, int]:
    """System health check and GenAI status."""
    return jsonify({
        "status": "healthy",
        "service": "Celebrio AI Celebration & Event Planner",
        "version": "1.1.0",
        "genai_active": engine.is_genai_enabled()
    }), 200


@app.route("/api/presets", methods=["GET"])
def get_presets() -> Response:
    """
    Returns supported celebration personas and initial configuration templates.
    Uses ETag and Cache-Control headers for high efficiency.
    """
    if request.headers.get("If-None-Match") == _PRESETS_ETAG:
        return Response(status=304)

    response = Response(_PRESETS_JSON, mimetype="application/json")
    response.headers["ETag"] = _PRESETS_ETAG
    response.headers["Cache-Control"] = "public, max-age=3600"
    return response


@app.route("/api/validate", methods=["POST"])
def validate_payload() -> Tuple[Response, int]:
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
    except (CelebrioValidationError, ValueError) as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.error("Validation error: %s", e)
        return jsonify({"success": False, "error": "Invalid request body format."}), 400


@app.route("/api/generate-plan", methods=["POST"])
def generate_plan() -> Tuple[Response, int]:
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
    except (CelebrioValidationError, ValueError) as ve:
        return jsonify({"success": False, "error": str(ve)}), 400
    except Exception as e:
        logger.exception("Plan generation error: %s", e)
        return jsonify({
            "success": False,
            "error": "Failed to synthesize event plan. Please check inputs."
        }), 500


@app.route("/api/chat", methods=["POST"])
def chat() -> Tuple[Response, int]:
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
        logger.exception("Chat endpoint error: %s", e)
        return jsonify({"success": False, "error": "Assistant temporarily unavailable."}), 500


@app.route("/api/vendor-inquiry", methods=["POST"])
def vendor_inquiry() -> Tuple[Response, int]:
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
        logger.exception("Vendor inquiry error: %s", e)
        return jsonify({"success": False, "error": "Failed to generate vendor inquiry."}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    debug_mode = os.getenv("DEBUG", "False").lower() in ("true", "1", "t")
    logger.info(
        "Starting Celebrio AI Planner on http://localhost:%d (GenAI active: %s)",
        port, engine.is_genai_enabled()
    )
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
