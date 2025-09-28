# routes/auth.py

from flask import Blueprint, request, jsonify
from supabase_client import supabase
from utils.jwt import verify_jwt

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        response = supabase.auth.sign_up({"email": email, "password": password})

        if response.user is None:
            return jsonify({"error": "Signup failed"}), 400

        return (
            jsonify({"user": {"id": response.user.id, "email": response.user.email}}),
            200,
        )

    except Exception as e:
        print(f"Supabase signup error: {e}")
        return jsonify({"error": "Unexpected error during signup"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    response = supabase.auth.sign_in_with_password(
        {"email": email, "password": password}
    )

    if not response.user or not response.session:
        return jsonify({"error": "Invalid login"}), 400

    return (
        jsonify(
            {
                "access_token": response.session.access_token,
                "user": {"id": response.user.id, "email": response.user.email},
                "refresh_token": response.session.refresh_token
            }
        ),
        200,
    )


@auth_bp.route("/session", methods=["GET"])
def get_session():
    auth_header = request.headers.get("Authorization")

    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    access_token = auth_header.split(" ")[1]
    response = supabase.auth.get_user(access_token)

    if response.get("error"):
        return jsonify({"error": response["error"]["message"]}), 401

    return jsonify({"user": response["data"]["user"]}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    # Supabase client-side logout — server does not manage sessions directly.
    return jsonify({"message": "Client should delete token"}), 200


@auth_bp.route("/verify", methods=["GET"])
def verify_token():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"error": "Missing or invalid Authorization header"}), 401

    token = auth_header.split(" ")[1]

    try:
        payload = verify_jwt(token)
        return (
            jsonify(
                {
                    "valid": True,
                    "user_id": payload["sub"],
                    "email": payload.get("email"),
                    "exp": payload.get("exp"),
                }
            ),
            200,
        )
    except ValueError as e:
        return jsonify({"valid": False, "error": str(e)}), 401


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    response = supabase.auth.reset_password_for_email(email)

    if response.get("error"):
        return jsonify({"error": response["error"]["message"]}), 400

    return jsonify({"message": "Password reset email sent"}), 200

@auth_bp.route("/refresh", methods=["POST"])
def refresh():
    data = request.get_json()
    refresh_token = data.get("refresh_token")

    if not refresh_token:
        return jsonify({"error": "Refresh token is required"}), 400

    try:
        response = supabase.auth.refresh_session(refresh_token)
        if not response.user or not response.session:
            return jsonify({"error": "Failed to refresh session"}), 400

        return jsonify({
            "access_token": response.session.access_token,
            "refresh_token": response.session.refresh_token,
            "user": {
                "id": response.user.id,
                "email": response.user.email
            }
        }), 200

    except Exception as e:
        print(f"Refresh error: {e}")
        return jsonify({"error": "Unexpected error during refresh"}), 500
