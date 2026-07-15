import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode

from google_auth_oauthlib.flow import Flow
from app.core.config import settings

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
]

_STATE_MAX_AGE_SECONDS = 600


def create_flow(state: str | None = None, code_verifier: str | None = None) -> Flow:
    config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    return Flow.from_client_config(
        config,
        scopes=SCOPES,
        state=state,
        redirect_uri=settings.google_redirect_uri,
        code_verifier=code_verifier,
        autogenerate_code_verifier=code_verifier is None,
    )


def _b64url_encode(raw: bytes) -> str:
    return urlsafe_b64encode(raw).decode().rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return urlsafe_b64decode(value + padding)


def create_oauth_state(code_verifier: str) -> str:
    """Signed state carrying PKCE verifier so callback works across reloads."""
    payload = {
        "ts": int(time.time()),
        "nonce": secrets.token_urlsafe(16),
        "cv": code_verifier,
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    return f"{body}.{sig}"


def parse_oauth_state(state: str) -> str:
    """Validate state and return code_verifier. Raises ValueError if invalid."""
    try:
        body, sig = state.rsplit(".", 1)
    except ValueError as exc:
        raise ValueError("malformed state") from exc

    expected = hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).hexdigest()[:32]
    if not hmac.compare_digest(sig, expected):
        raise ValueError("bad signature")

    payload = json.loads(_b64url_decode(body))
    if abs(int(time.time()) - int(payload["ts"])) > _STATE_MAX_AGE_SECONDS:
        raise ValueError("expired")
    code_verifier = payload.get("cv")
    if not code_verifier:
        raise ValueError("missing verifier")
    return code_verifier
