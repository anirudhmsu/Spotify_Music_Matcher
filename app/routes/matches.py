# app/routes/matches.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User
from app.models.music import UserArtist, UserAudioProfile
from app.services.scoring import score

router = APIRouter()

@router.get("/")
def get_matches(user_id: int = Query(...), limit: int = 20, session: Session = Depends(get_session)):
    me = session.get(User, user_id)
    if not me: return []

    def pack(user_id: int):
        artists = [r.artist_id for r in session.exec(
            select(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == "medium").order_by(UserArtist.rank)
        )]
        genres = []
        for r in session.exec(select(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == "medium")):
            if r.genres: genres += r.genres.split(",")
        prof = session.get(UserAudioProfile, user_id)
        audio = [prof.tempo, prof.energy, prof.valence, prof.danceability, prof.acousticness, prof.loudness] if prof else [0,0,0,0,0,0]
        return {"artists": artists, "genres": genres, "audio": audio}

    me_pack = pack(me.id)
    candidates = session.exec(select(User).where(User.id != me.id)).all()

    scored = []
    for u in candidates:
        s = score(me_pack, pack(u.id))
        scored.append({"user_id": u.id, "display_name": u.display_name, "avatar_url": u.avatar_url, "score": round(s, 4)})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
