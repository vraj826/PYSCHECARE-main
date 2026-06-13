import base64
import hmac
import hashlib
import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from chatbot_integration import get_chatbot_response
from validation import validate_chat_payload
from crisis_detection import detect_crisis_risk, log_crisis_event
from medication_manager import MedicationManager, MedicationValidationError

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024
medication_manager = MedicationManager()

ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN")
if not ALLOWED_ORIGIN:
    raise ValueError(
        "CRITICAL: ALLOWED_ORIGIN environment variable is not set! "
        "Refusing to start with insecure CORS."
    )
CORS(app, origins=[ALLOWED_ORIGIN])


@app.before_request
def verify_origin():
    origin = request.headers.get("Origin")
    if not origin:
        return jsonify({"error": "Missing Origin header"}), 403
    if origin != ALLOWED_ORIGIN:
        return jsonify({"error": "Origin not allowed"}), 403


limiter = Limiter(get_remote_address, app=app, default_limits=["30 per minute"])
CHAT_API_SECRET = os.environ.get("CHAT_API_SECRET", "")


def _verify_chat_token(token: str) -> str:
    """Validate the HMAC chat token and return the extracted session ID."""
    if not CHAT_API_SECRET or not token or "." not in token:
        return None

    try:
        payload, signature = token.split(".", 1)
        expected_sig = hmac.new(
            CHAT_API_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_sig, signature):
            return None

        decoded_payload = base64.b64decode(payload).decode("utf-8")
        session_id, username = decoded_payload.split("|", 1)
        return session_id
    except Exception:
        return None


@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")
def chat():
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    user_id = _verify_chat_token(token)
    if not user_id:
        return jsonify({
            "error": "Unauthorized. Please log in to use the chatbot."
        }), 401

    data = request.get_json(silent=True)
    validation_error = validate_chat_payload(data)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    risk = detect_crisis_risk(data["message"])
    log_crisis_event(risk, user_id)

    response = get_chatbot_response(data["message"], user_id)
    return jsonify({"response": response, "session_id": user_id, "risk": risk})


@app.route("/medications", methods=["GET"])
def medications_index():
    return jsonify({
        "medications": medication_manager.list_medications(),
        "logs": medication_manager.list_logs(),
        "stats": medication_manager.adherence_stats(),
        "due_today": medication_manager.due_today(),
    })


@app.route("/medications", methods=["POST"])
def medications_create():
    data = request.get_json(silent=True) or {}
    try:
        medication = medication_manager.create_medication(data)
    except MedicationValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"medication": medication}), 201


@app.route("/medications/<medication_id>", methods=["PUT"])
def medications_update(medication_id):
    data = request.get_json(silent=True) or {}
    try:
        medication = medication_manager.update_medication(medication_id, data)
    except MedicationValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    if not medication:
        return jsonify({"error": "Medication not found."}), 404
    return jsonify({"medication": medication})


@app.route("/medications/<medication_id>", methods=["DELETE"])
def medications_delete(medication_id):
    if not medication_manager.delete_medication(medication_id):
        return jsonify({"error": "Medication not found."}), 404
    return jsonify({"deleted": True})


@app.route("/medications/<medication_id>/adherence", methods=["POST"])
def medications_adherence(medication_id):
    data = request.get_json(silent=True) or {}
    try:
        log_entry = medication_manager.log_adherence(
            medication_id,
            data.get("status"),
            data.get("date"),
        )
    except MedicationValidationError as exc:
        return jsonify({"error": str(exc)}), 400
    if not log_entry:
        return jsonify({"error": "Medication not found."}), 404
    return jsonify({"log": log_entry}), 201


@app.errorhandler(413)
def payload_too_large(error):
    return jsonify({"error": "Request body is too large."}), 413


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Invalid request."}), 400


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
