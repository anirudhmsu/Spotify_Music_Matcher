# app/services/spotify.py
import httpx, os
from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.models.user import SpotifyToken
from fastapi import HTTPException

AUTH_URL = "https://accounts.spotify.com/api/token"
BASE = "https://api.spotify.com/v1"

async def ensure_token(user_id: int, session: Session) -> str:
    tok = session.exec(select(SpotifyToken).where(SpotifyToken.user_id == user_id)).first()
    if not tok:
        raise HTTPException(status_code=401, detail="No Spotify token for this user. Please login via /auth/login.")
    if tok.expires_at > datetime.utcnow():
        return tok.access_token
    # refresh
    if not tok.refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing. Please re-authenticate with Spotify.")
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": tok.refresh_token,
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET"),
        }
        r = await client.post(AUTH_URL, data=data, timeout=30)
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(status_code=401, detail=f"Failed to refresh token: {e.response.text}")
        payload = r.json()
        tok.access_token = payload["access_token"]
        tok.expires_at = datetime.utcnow() + timedelta(seconds=payload.get("expires_in", 3600) - 60)
        session.add(tok)
        session.commit()
        return tok.access_token

async def get_top(token: str, kind: str, term: str):
    url = f"{BASE}/me/top/{kind}"
    params = {"time_range": f"{term}_term", "limit": 50}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        r.raise_for_status()
        return r.json()["items"]

async def get_audio_features(token: str, track_ids: list[str]):
    if not track_ids: return []
    async with httpx.AsyncClient() as client:
        r = await client.get(f"{BASE}/audio-features", headers={"Authorization": f"Bearer {token}"}, params={"ids": ",".join(track_ids[:100])}, timeout=30)
        r.raise_for_status()
        return r.json()["audio_features"]


async def get_recently_played(token: str, limit: int = 50):
    url = f"{BASE}/me/player/recently-played"
    params = {"limit": limit}
    async with httpx.AsyncClient() as client:
        r = await client.get(url, headers={"Authorization": f"Bearer {token}"}, params=params, timeout=30)
        r.raise_for_status()
        return r.json().get("items", [])
