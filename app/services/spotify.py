# app/services/spotify.py
import httpx, os
from sqlmodel import Session, select
from datetime import datetime, timedelta
from app.models.user import SpotifyToken

AUTH_URL = "https://accounts.spotify.com/api/token"
BASE = "https://api.spotify.com/v1"

async def ensure_token(user_id: int, session: Session) -> str:
    tok = session.exec(select(SpotifyToken).where(SpotifyToken.user_id == user_id)).first()
    assert tok
    if tok.expires_at > datetime.utcnow():
        return tok.access_token
    # refresh
    async with httpx.AsyncClient() as client:
        data = {
            "grant_type": "refresh_token",
            "refresh_token": tok.refresh_token,
            "client_id": os.getenv("SPOTIFY_CLIENT_ID"),
            "client_secret": os.getenv("SPOTIFY_CLIENT_SECRET"),
        }
        r = await client.post(AUTH_URL, data=data, timeout=30)
        r.raise_for_status()
        payload = r.json()
        tok.access_token = payload["access_token"]
        tok.expires_at = datetime.utcnow() + timedelta(seconds=payload["expires_in"] - 60)
        session.add(tok); session.commit()
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
