"""
JWT Authentication Middleware

Provides authentication decorators and helpers for protecting Flask routes.
"""

import os
import logging
from functools import wraps
from flask import request, jsonify, g
import requests
from services.database import Supa

logger = logging.getLogger(__name__)

# Initialize database connection
db = Supa()

# Auth service URL from environment
AUTH_SERVICE_URL = os.getenv('AUTH_SERVICE_URL', 'http://127.0.0.1:8081')


class AuthError(Exception):
    """Custom exception for authentication errors"""
    def __init__(self, message, status_code=401):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def extract_token_from_header():
    """
    Extract JWT token from Authorization header

    Returns:
        str: The JWT token

    Raises:
        AuthError: If token is missing or malformed
    """
    auth_header = request.headers.get('Authorization')

    if not auth_header:
        raise AuthError('Authorization header is missing', 401)

    parts = auth_header.split()

    if len(parts) != 2 or parts[0].lower() != 'bearer':
        raise AuthError('Authorization header must be in format: Bearer <token>', 401)

    return parts[1]


def verify_token(token):
    """
    Verify JWT token by fetching user info from auth service

    Args:
        token (str): The JWT token to verify

    Returns:
        dict: Token claims including user_id

    Raises:
        AuthError: If token is invalid or verification fails
    """
    try:
        # Call auth service /user endpoint to verify token and get user info
        # This is the standard way to validate JWTs with Supabase Auth
        logger.info(f"Verifying token with auth service at {AUTH_SERVICE_URL}/user")
        response = requests.get(
            f'{AUTH_SERVICE_URL}/user',
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )

        logger.info(f"Auth service response: status={response.status_code}")

        if response.status_code != 200:
            logger.warning(f"Auth service returned status {response.status_code}: {response.text[:200]}")
            raise AuthError('Invalid or expired token', 401)

        data = response.json()

        # Extract user ID from the response
        # Supabase returns user info in different formats depending on the endpoint
        user_id = (
            data.get('id') or
            data.get('user_id') or
            data.get('sub') or
            (data.get('user', {}).get('id') if isinstance(data.get('user'), dict) else None)
        )

        if not user_id:
            logger.error(f"No user_id found in token response. Data: {data}")
            raise AuthError('Token missing user identification', 401)

        # Check if user is admin from public.users table
        is_admin = False
        try:
            logger.info(f"Checking admin status for user {user_id} from public.users table")
            admin_result = db.client.table("users").select("is_admin").eq("id", user_id).single().execute()
            logger.info(f"Admin query result: {admin_result.data}")
            if admin_result.data and admin_result.data.get("is_admin"):
                is_admin = True
                logger.info(f"✓ User {user_id} IS AN ADMIN")
            else:
                logger.info(f"✗ User {user_id} is NOT an admin (data: {admin_result.data})")
        except Exception as e:
            # Default to non-admin if query fails or user not found
            logger.warning(f"Failed to check admin status for user {user_id}: {e}")
            is_admin = False

        logger.info(f"Token verified successfully for user {user_id}")
        return {
            'user_id': user_id,
            'is_admin': is_admin,
            'claims': data
        }

    except requests.RequestException as e:
        logger.error(f"Auth service communication error: {e}")
        raise AuthError('Unable to verify token with auth service', 503)


def require_auth(f):
    """
    Decorator to protect routes with JWT authentication

    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            user_id = g.user_id
            return jsonify({'message': 'Success'})
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Extract and verify token
            token = extract_token_from_header()
            token_data = verify_token(token)

            # Attach user_id and is_admin to Flask request context
            g.user_id = token_data['user_id']
            g.is_admin = token_data.get('is_admin', False)
            g.token_claims = token_data['claims']

            logger.info(f"Auth context set: user_id={g.user_id}, is_admin={g.is_admin}")

            # Call the actual route function
            return f(*args, **kwargs)

        except AuthError as e:
            logger.warning(f"Authentication failed: {e.message}")
            return jsonify({
                'success': False,
                'error': e.message
            }), e.status_code
        except Exception as e:
            logger.error(f"Unexpected auth error: {e}")
            return jsonify({
                'success': False,
                'error': 'Authentication error'
            }), 500

    return decorated_function
