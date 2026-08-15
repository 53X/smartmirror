"""Staff JWT (Supabase) and kiosk device-token authentication."""

from __future__ import annotations

import hmac
from typing import Literal

import httpx
import jwt
from fastapi import Header, HTTPException
from smartmirror_shared.logging_config import configure_service_logging

from app.settings import settings

logger = configure_service_logging("gateway", settings.log_level)

Role = Literal["staff", "kiosk"]


def require_staff(
    authorization: str | None = Header(default=None),
) -> Role:
    """Allow staff routes with a verified Supabase JWT or local bypass."""
    if settings.auth_dev_bypass and authorization == "Bearer staff-dev":
        return "staff"
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Staff bearer token required")
    token = authorization.removeprefix("Bearer ").strip()
    _verify_supabase_jwt(token)
    return "staff"


def require_kiosk(
    x_kiosk_token: str | None = Header(default=None, alias="X-Kiosk-Token"),
) -> Role:
    """Allow kiosk routes only with the store device token."""
    expected = settings.kiosk_device_token.encode("utf-8")
    provided = (x_kiosk_token or "").encode("utf-8")
    if not expected or not hmac.compare_digest(provided, expected):
        raise HTTPException(status_code=401, detail="Invalid kiosk device token")
    return "kiosk"


def _verify_supabase_jwt(token: str) -> None:
    if settings.supabase_jwt_secret:
        try:
            jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            return
        except jwt.PyJWTError as exc:
            raise HTTPException(status_code=401, detail="Invalid staff token") from exc

    if settings.supabase_url:
        jwks_url = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
        try:
            jwks = httpx.get(jwks_url, timeout=5).json()
            header = jwt.get_unverified_header(token)
            key = next((item for item in jwks.get("keys", []) if item.get("kid") == header.get("kid")), None)
            if key is None:
                raise HTTPException(status_code=401, detail="Unknown token key")
            jwt.decode(token, jwt.PyJWK.from_dict(key).key, algorithms=["ES256", "RS256"], options={"verify_aud": False})
            return
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001
            logger.warning("jwks_verify_failed")
            raise HTTPException(status_code=401, detail="Invalid staff token") from exc

    raise HTTPException(
        status_code=401,
        detail="Staff auth is not configured. Set SUPABASE_URL or AUTH_DEV_BYPASS for local use.",
    )
