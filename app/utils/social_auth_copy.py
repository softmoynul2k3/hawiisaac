import re
from dataclasses import dataclass
from typing import Optional

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from jose import jwt

from app.config import settings
from applications.user.models import User


APPLE_ISSUER = "https://appleid.apple.com"
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"


def _split_csv(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _normalize_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _username_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "", value.strip().lower())
    return slug[:120] or "user"


async def _build_unique_username(*candidates: Optional[str]) -> str:
    fallback = "user"
    base = fallback

    for candidate in candidates:
        normalized = _normalize_text(candidate)
        if not normalized:
            continue
        base = _username_slug(normalized)
        if base:
            break

    username = base
    suffix = 1
    while await User.filter(username=username).exists():
        suffix += 1
        username = f"{base}{suffix}"
        if len(username) > 120:
            username = f"{base[:120-len(str(suffix))]}{suffix}"

    return username


@dataclass
class SocialProfile:
    provider: str
    provider_user_id: str
    email: Optional[str]
    email_verified: bool
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    photo: Optional[str] = None


async def verify_google_id_token(token: str) -> SocialProfile:
    client_ids = _split_csv(getattr(settings, "GOOGLE_CLIENT_IDS", ""))
    if not client_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GOOGLE_CLIENT_IDS is not configured.",
        )

    try:
        id_info = google_id_token.verify_oauth2_token(
            token.strip(),
            google_requests.Request(),
            audience=None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token.") from exc

    audience = id_info.get("aud")
    if audience not in client_ids:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token audience mismatch.")

    issuer = id_info.get("iss")
    if issuer not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Google token issuer.")

    provider_user_id = id_info.get("sub")
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Google token missing subject.")

    email = _normalize_text(id_info.get("email"))

    return SocialProfile(
        provider="google",
        provider_user_id=provider_user_id,
        email=email.lower() if email else None,
        email_verified=_to_bool(id_info.get("email_verified")),
        first_name=_normalize_text(id_info.get("given_name")),
        last_name=_normalize_text(id_info.get("family_name")),
        photo=_normalize_text(id_info.get("picture")),
    )


async def _fetch_apple_jwks() -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(APPLE_JWKS_URL)
            response.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to verify Apple token right now.",
        ) from exc

    jwks = response.json()
    if not isinstance(jwks, dict) or "keys" not in jwks:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Invalid Apple JWKS response.",
        )
    return jwks


async def verify_apple_id_token(
    token: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
) -> SocialProfile:
    client_ids = _split_csv(getattr(settings, "APPLE_CLIENT_IDS", ""))
    if not client_ids:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="APPLE_CLIENT_IDS is not configured.",
        )

    token = token.strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="id_token is required.")

    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Apple token header.") from exc

    kid = header.get("kid")
    jwks = await _fetch_apple_jwks()

    key_data = next((key for key in jwks["keys"] if key.get("kid") == kid), None)
    if not key_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Apple signing key not found.")

    try:
        payload = jwt.decode(
            token,
            key_data,
            algorithms=["RS256"],
            options={"verify_at_hash": False, "verify_aud": False, "verify_iss": False},
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Apple token.") from exc

    if payload.get("iss") != APPLE_ISSUER:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Apple token issuer.")

    audience = payload.get("aud")
    if audience not in client_ids:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Apple token audience mismatch.")

    provider_user_id = payload.get("sub")
    if not provider_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Apple token missing subject.")

    email = _normalize_text(payload.get("email"))

    return SocialProfile(
        provider="apple",
        provider_user_id=provider_user_id,
        email=email.lower() if email else None,
        email_verified=_to_bool(payload.get("email_verified")),
        first_name=_normalize_text(first_name),
        last_name=_normalize_text(last_name),
    )


async def get_or_create_social_user(profile: SocialProfile) -> tuple[User, bool]:
    provider_field = "google_id" if profile.provider == "google" else "apple_id"

    user = await User.get_or_none(**{provider_field: profile.provider_user_id})
    created = False

    if user is None and profile.email:
        user = await User.get_or_none(email=profile.email)

    if user is None:
        username = await _build_unique_username(
            profile.email.split("@")[0] if profile.email else None,
            profile.first_name,
            profile.provider,
        )
        user = await User.create(
            username=username,
            email=profile.email,
            first_name=profile.first_name,
            last_name=profile.last_name,
            photo=profile.photo,
            auth_provider=profile.provider,
            **{provider_field: profile.provider_user_id},
        )
        created = True
        return user, created

    updated = False
    if getattr(user, provider_field) != profile.provider_user_id:
        setattr(user, provider_field, profile.provider_user_id)
        updated = True
    if profile.email and user.email != profile.email:
        user.email = profile.email
        updated = True
    if profile.first_name and not user.first_name:
        user.first_name = profile.first_name
        updated = True
    if profile.last_name and not user.last_name:
        user.last_name = profile.last_name
        updated = True
    if profile.photo and not user.photo:
        user.photo = profile.photo
        updated = True
    if user.auth_provider != profile.provider:
        user.auth_provider = profile.provider
        updated = True

    if updated:
        await user.save()

    return user, created
