import jwt
from jwt import PyJWKClient

import os

SUPABASE_URL = os.environ["SUPABASE_URL"]

JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"


def verify_jwt(token: str):
    try:
        jwks_client = PyJWKClient(JWKS_URL)
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=None,  # Optional
            options={"verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid token")
