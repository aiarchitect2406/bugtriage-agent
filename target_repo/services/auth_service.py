"""Authentication and JWT Token Validation Service."""

from typing import Dict, Any, Optional
import time

def verify_jwt_token(token_payload: Dict[str, Any]) -> Dict[str, Any]:
    """Verifies a JWT token payload.

    BUG: If 'exp' timestamp is missing or not an integer, raises ValueError/TypeError.
    """
    token_str = token_payload.get("token")
    if not token_str:
        return {"valid": False, "reason": "Missing token"}

    # Intentional bug: assumes exp is always present and an int
    exp_time = token_payload.get("exp")
    current_time = time.time()

    if exp_time is not None and exp_time < current_time:
        return {"valid": False, "reason": "Token expired"}

    return {
        "valid": True,
        "user_id": token_payload.get("sub", "anonymous"),
        "role": token_payload.get("role", "viewer")
    }
