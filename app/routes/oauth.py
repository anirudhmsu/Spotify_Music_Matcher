# app/routes/oauth.py
from fastapi import APIRouter, Depends, Request, Response, HTTPException
from authlib.integrations.starlette_client import OAuth
from starlette.responses import RedirectResponse
import os, time
from datetime import datetime, timedelta
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User, SpotifyToken
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
oauth = OAuth()
oauth.register(
    name="spotify",
    client_id=os.getenv("SPOTIFY_CLIENT_ID"),
    client_secret=os.getenv("SPOTIFY_CLIENT_SECRET"),
    access_token_url="https://accounts.spotify.com/api/token",
    authorize_url="https://accounts.spotify.com/authorize",
    api_base_url="https://api.spotify.com/v1/",
    client_kwargs={"scope": "user-read-email user-top-read"},
)

@router.get("/login")
async def login_via_spotify(request: Request):
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")
    return await oauth.spotify.authorize_redirect(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, session: Session = Depends(get_session)):
    try:
        # Workaround for state mismatch in some local setups:
        # If the state in the query doesn't match what's in the session, align it
        qs_state = request.query_params.get("state")
        if qs_state:
            # Authlib commonly uses this key to store state in the session
            state_key = "oauth_spotify_state"
            if request.session.get(state_key) != qs_state:
                request.session[state_key] = qs_state
        token = await oauth.spotify.authorize_access_token(request)
    except Exception as e:
        logger.exception("Token exchange failed")
        raise HTTPException(400, detail=f"Token exchange failed: {e}")

    if not token or "access_token" not in token:
        raise HTTPException(400, detail=f"Invalid token payload: {token}")

    # get profile
    # Leading slash matters with some base_url joiners
    resp = await oauth.spotify.get("/me", token=token)
    if getattr(resp, "status_code", 200) != 200:
        raise HTTPException(resp.status_code, detail=f"Spotify /me error: {getattr(resp, 'text', '')}")
    me = resp.json() or {}
    spotify_id = me.get("id")
    if not spotify_id:
        raise HTTPException(400, detail=f"Missing id in Spotify profile: {me}")
    # upsert user
    user = session.exec(select(User).where(User.spotify_id == spotify_id)).first()
    if not user:
        user = User(
            spotify_id=spotify_id,
            display_name=me.get("display_name"),
            avatar_url=(me.get("images") or [{}])[0].get("url"),
            country=(me.get("country")),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    # store tokens
    expires_at = datetime.utcnow() + timedelta(seconds=token.get("expires_in", 3600) - 60)
    # Some providers don't resend refresh_token on subsequent logins
    refresh_token = token.get("refresh_token")
    if not refresh_token:
        existing = session.exec(select(SpotifyToken).where(SpotifyToken.user_id == user.id)).first()
        if existing:
            refresh_token = existing.refresh_token
        else:
            refresh_token = ""
    session.merge(SpotifyToken(
        user_id=user.id,
        access_token=token["access_token"],
        refresh_token=refresh_token or "",
        expires_at=expires_at
    ))
    session.commit()
    # Kick off initial ingest after auth
    return RedirectResponse(url=f"/ingest/spotify?user_id={user.id}")


@router.get("/logout")
def logout(response: Response):
    # Clear session cookie to avoid stale state
    response = RedirectResponse(url="/")
    response.delete_cookie("sm_session", path="/")
    return response
