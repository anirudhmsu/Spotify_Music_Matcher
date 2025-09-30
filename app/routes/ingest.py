# app/routes/ingest.py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select, delete
from app.db import get_session
from app.services.spotify import ensure_token, get_top, get_audio_features
from app.models.user import User
from app.models.music import UserArtist, UserTrack, UserAudioProfile
from statistics import mean

router = APIRouter()

@router.get("/spotify")
async def ingest_spotify(user_id: int = Query(...), session: Session = Depends(get_session)):
    user = session.get(User, user_id)
    if not user: raise HTTPException(404, "User not found")
    token = await ensure_token(user_id, session)

    for term in ["short", "medium", "long"]:
        artists = await get_top(token, "artists", term)
        tracks  = await get_top(token, "tracks", term)
        # wipe & insert (POC simplicity) via ORM deletes
        session.exec(delete(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == term))
        session.exec(delete(UserTrack).where(UserTrack.user_id == user_id, UserTrack.term == term))
        for rank, a in enumerate(artists, start=1):
            session.add(UserArtist(
                user_id=user_id, term=term,
                artist_id=a["id"], artist_name=a["name"],
                genres=",".join(a.get("genres", [])),
                popularity=a.get("popularity", 0), rank=rank
            ))
        for rank, t in enumerate(tracks, start=1):
            session.add(UserTrack(
                user_id=user_id, term=term,
                track_id=t["id"], track_name=t["name"],
                artist_ids=",".join([ar["id"] for ar in t["artists"]]),
                popularity=t.get("popularity", 0), rank=rank
            ))
        session.commit()

    # audio centroid from top tracks (medium term as baseline)
    rows = session.exec(
        select(UserTrack.track_id).where(UserTrack.user_id == user_id, UserTrack.term == "medium").order_by(UserTrack.rank).limit(50)
    ).all()
    ids = [tid for (tid,) in rows]
    feats = await get_audio_features(token, ids)
    if feats:
        def col(k): return [f[k] for f in feats if f]
        profile = UserAudioProfile(
            user_id=user_id,
            tempo=mean(col("tempo")),
            energy=mean(col("energy")),
            valence=mean(col("valence")),
            danceability=mean(col("danceability")),
            acousticness=mean(col("acousticness")),
            loudness=mean(col("loudness"))
        )
        session.merge(profile); session.commit()
    return {"ok": True}
