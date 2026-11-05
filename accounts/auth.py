from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from ninja.security import HttpBearer


def create_token(user_id: int, token_type: str, minutes: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": token_type,  # "access" or "refresh"
        "iat": now,
        "exp": now + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_token_pair(user_id: int) -> dict:
    return {
        "access": create_token(user_id, "access", settings.JWT_ACCESS_MINUTES),
        "refresh": create_token(user_id, "refresh", settings.JWT_REFRESH_MINUTES),
    }


def decode_token(token: str, expected_type: str):
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != expected_type:
        return None
    return payload


class JWTAuth(HttpBearer):
    """Reads 'Authorization: Bearer <access token>'. The user ends up in request.auth."""

    def authenticate(self, request, token):
        payload = decode_token(token, "access")
        if not payload:
            return None
        User = get_user_model()
        return User.objects.filter(pk=payload["sub"], is_active=True).first()