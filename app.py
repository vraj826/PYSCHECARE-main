import hmac
import hashlib
import os
import uuid
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from chatbot_integration import get_chatbot_response

app = Flask(__name__)

# ── CORS ────────────────────────────────────────────────────────────────────
# Read allowed origin from environment variable — fail closed if not set
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN")
if not ALLOWED_ORIGIN:
    raise ValueError(
        "CRITICAL: ALLOWED_ORIGIN environment variable is not set! "
        "Refusing to start with insecure CORS."
    )
CORS(app, origins=[ALLOWED_ORIGIN])

@app.before_request
def verify_origin():
    """Harden CORS by rejecting requests missing or disallowed Origin header."""
    origin = request.headers.get("Origin")
    if not origin:
        return jsonify({"error": "Missing Origin header"}), 403
    if origin != ALLOWED_ORIGIN:
        return jsonify({"error": "Origin not allowed"}), 403

# ── Rate limiting ────────────────────────────────────────────────────────────
limiter = Limiter(get_remote_address, app=app, default_limits=["30 per minute"])

# ── Shared secret for chat token validation ──────────────────────────────────
# Must match the value set in chatBot.php (CHAT_API_SECRET env var).
# If not set, the endpoint refuses ALL requests — fail closed.
CHAT_API_SECRET = os.environ.get("CHAT_API_SECRET", "")


def _verify_chat_token(token: str) -> bool:
    """
    Validate the HMAC chat token sent by the frontend.

    The token is produced by chatBot.php as:
        hash_hmac('sha256', session_id + '|' + username, secret)

    We can't reconstruct the exact input here (we don't have the PHP session),
    so we verify that the token is a valid 64-char SHA-256 hex string AND that
    the secret is configured.  A proper production setup would use a shared
    session store (Redis, database) to verify the token fully.

    For now this blocks:
    - All requests with no Authorization header (unauthenticated browsers)
    - All requests with a malformed token (not a 64-hex SHA-256 string)
    - All requests when CHAT_API_SECRET is not configured (fail-closed)
    """
    if not CHAT_API_SECRET:
        return False  # Fail closed — no secret means no access
    if not token or len(token) != 64:
        return False
    try:
        int(token, 16)  # Valid hex string?
    except ValueError:
        return False
    return True


@app.route("/chat", methods=["POST"])
@limiter.limit("30 per minute")
def chat():
    # ── Authentication check ─────────────────────────────────────────────────
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.removeprefix("Bearer ").strip()

    if not _verify_chat_token(token):
        return jsonify({
            "error": "Unauthorized. Please log in to use the chatbot."
        }), 401

    # ── Payload validation ───────────────────────────────────────────────────
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Missing message"}), 400

    # Use session ID from request or generate a unique one
    user_id = data.get("session_id") or str(uuid.uuid4())

    response = get_chatbot_response(data["message"], user_id)
    return jsonify({"response": response, "session_id": user_id})


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
