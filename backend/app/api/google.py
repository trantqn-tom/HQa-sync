import secrets
from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import encrypt_text
from app.models.google_connection import GoogleConnection
from app.models.user import User
from app.services.google_oauth import create_flow, create_oauth_state, parse_oauth_state

router = APIRouter(prefix="/google", tags=["Google OAuth"])


@router.get("/status")
def status(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.scalar(select(GoogleConnection).where(GoogleConnection.is_active.is_(True)).order_by(GoogleConnection.id.desc()))
    return {"connected": bool(item), "email": item.google_email if item else None}


@router.get("/connect")
def connect(_: User = Depends(get_current_user)):
    code_verifier = secrets.token_urlsafe(64)
    state = create_oauth_state(code_verifier)
    flow = create_flow(state=state, code_verifier=code_verifier)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return {"authorization_url": url}


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        code_verifier = parse_oauth_state(state)
    except ValueError:
        raise HTTPException(status_code=400, detail="OAuth state không hợp lệ") from None

    flow = create_flow(state=state, code_verifier=code_verifier)
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Đổi code OAuth thất bại: {exc}") from exc

    credentials = flow.credentials
    email = None
    if credentials.id_token:
        claims = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
        email = claims.get("email")

    for old in db.scalars(select(GoogleConnection).where(GoogleConnection.is_active.is_(True))):
        old.is_active = False

    db.add(GoogleConnection(
        google_email=email,
        access_token_encrypted=encrypt_text(credentials.token),
        refresh_token_encrypted=encrypt_text(credentials.refresh_token),
        token_uri=credentials.token_uri,
        scopes=" ".join(credentials.scopes or []),
        token_expiry=(
            credentials.expiry.replace(tzinfo=timezone.utc)
            if credentials.expiry and not credentials.expiry.tzinfo
            else credentials.expiry
        ),
        is_active=True,
    ))
    db.commit()
    return RedirectResponse(f"{settings.frontend_url}/settings?google=connected")
