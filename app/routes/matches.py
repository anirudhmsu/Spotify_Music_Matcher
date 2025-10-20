# app/routes/matches.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User, UserSettings
from app.models.music import UserArtist, UserAudioProfile, UserTrack, RecentTrack
from app.services.scoring import score, jaccard, audio_affinity, normalize_audio

router = APIRouter()

def _parse_blocked(csv_ids: str | None) -> set[int]:
    if not csv_ids:
        return set()
    out: set[int] = set()
    for p in csv_ids.split(","):
        p = p.strip()
        if not p:
            continue
        try:
            out.add(int(p))
        except ValueError:
            continue
    return out


@router.get("/")
def get_matches(
    user_id: int = Query(...),
    limit: int = 20,
    cursor: int = 0,
    country: str | None = None,
    min_score: float | None = None,
    min_shared_artists: int = 0,
    has_genres: str | None = None,
    session: Session = Depends(get_session),
):
    me = session.get(User, user_id)
    if not me: return []
    my_settings = session.get(UserSettings, me.id)
    my_blocked = _parse_blocked(my_settings.blocked_user_ids) if my_settings else set()

    def pack(user_id: int):
        artists = [
            r.artist_id
            for r in session.exec(
                select(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == "medium").order_by(UserArtist.rank)
            )
        ]
        genres_list = []
        for r in session.exec(select(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == "medium")):
            if r.genres:
                genres_list += [g for g in r.genres.split(",") if g]
        genres = list(set(genres_list))
        prof = session.get(UserAudioProfile, user_id)
        audio = [
            prof.tempo,
            prof.energy,
            prof.valence,
            prof.danceability,
            prof.acousticness,
            prof.loudness,
        ] if prof else [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        return {"artists": artists, "genres": genres, "audio": audio}

    me_pack = pack(me.id)
    candidates = session.exec(select(User).where(User.id != me.id)).all()

    scored = []
    for u in candidates:
        # Privacy controls and blocks
        s_other = session.get(UserSettings, u.id)
        if s_other and not s_other.is_public:
            continue
        other_blocked_me = _parse_blocked(s_other.blocked_user_ids) if s_other else set()
        if (u.id in my_blocked) or (me.id in other_blocked_me):
            continue
        if country and (u.country or "").upper() != country.upper():
            continue
        up = pack(u.id)
        s = score(me_pack, up)
        shared_artists = len(set(me_pack["artists"]) & set(up["artists"]))
        g_overlap = jaccard(me_pack["genres"], up["genres"]) if me_pack["genres"] or up["genres"] else 0.0
        a_aff = audio_affinity(me_pack["audio"], up["audio"])
        if min_shared_artists and shared_artists < min_shared_artists:
            continue
        if has_genres:
            required = {g.strip().lower() for g in has_genres.split(",") if g.strip()}
            if required and not (required & {g.lower() for g in up["genres"]}):
                continue
        if min_score is not None and s < float(min_score):
            continue
        scored.append({
            "user_id": u.id,
            "display_name": u.display_name,
            "avatar_url": u.avatar_url,
            "score": round(s, 4),
            "shared_artists_count": shared_artists,
            "genre_overlap": round(g_overlap, 4),
            "audio_affinity": round(a_aff, 4),
        })
    scored.sort(key=lambda x: x["score"], reverse=True)
    start = max(cursor, 0)
    return scored[start:start + max(1, min(limit, 100))]


@router.get("/explain")
def explain_match(
    user_id: int = Query(...),
    other_id: int = Query(...),
    session: Session = Depends(get_session),
):
    me = session.get(User, user_id)
    other = session.get(User, other_id)
    if not me or not other:
        raise HTTPException(status_code=404, detail="User not found")

    # Artists for medium term
    me_artists = list(session.exec(
        select(UserArtist).where(UserArtist.user_id == user_id, UserArtist.term == "medium").order_by(UserArtist.rank)
    ))
    other_artists = list(session.exec(
        select(UserArtist).where(UserArtist.user_id == other_id, UserArtist.term == "medium").order_by(UserArtist.rank)
    ))
    me_map = {a.artist_id: a for a in me_artists}
    other_map = {a.artist_id: a for a in other_artists}
    shared_ids = list(set(me_map.keys()) & set(other_map.keys()))
    shared = []
    for aid in shared_ids:
        shared.append({
            "id": aid,
            "name": me_map[aid].artist_name or other_map[aid].artist_name,
            "rank_me": me_map[aid].rank,
            "rank_other": other_map[aid].rank,
        })
    shared.sort(key=lambda x: (x["rank_me"] + x["rank_other"]))

    # Genres overlap and counts
    def expand_genres(rows):
        out = []
        for r in rows:
            if r.genres:
                out += [g for g in r.genres.split(",") if g]
        return out

    me_genres_list = expand_genres(me_artists)
    other_genres_list = expand_genres(other_artists)
    me_genres = set(me_genres_list)
    other_genres = set(other_genres_list)
    overlap_genres = list(me_genres & other_genres)
    # Counts per genre in each user
    def counts(gen_list):
        d = {}
        for g in gen_list:
            d[g] = d.get(g, 0) + 1
        return d
    me_counts = counts(me_genres_list)
    other_counts = counts(other_genres_list)
    shared_genres_ranked = [
        {
            "genre": g,
            "me_count": me_counts.get(g, 0),
            "other_count": other_counts.get(g, 0),
        }
        for g in overlap_genres
    ]
    shared_genres_ranked.sort(key=lambda x: (x["me_count"] + x["other_count"]), reverse=True)

    # Audio breakdown
    me_prof = session.get(UserAudioProfile, user_id)
    other_prof = session.get(UserAudioProfile, other_id)
    me_audio = [
        me_prof.tempo, me_prof.energy, me_prof.valence, me_prof.danceability, me_prof.acousticness, me_prof.loudness
    ] if me_prof else [0.0] * 6
    other_audio = [
        other_prof.tempo, other_prof.energy, other_prof.valence, other_prof.danceability, other_prof.acousticness, other_prof.loudness
    ] if other_prof else [0.0] * 6
    me_audio_norm = normalize_audio(me_audio)
    other_audio_norm = normalize_audio(other_audio)
    dims = ["tempo", "energy", "valence", "danceability", "acousticness", "loudness"]
    audio_breakdown = []
    for i, dname in enumerate(dims):
        audio_breakdown.append({
            "dimension": dname,
            "me": me_audio[i],
            "other": other_audio[i],
            "me_norm": me_audio_norm[i],
            "other_norm": other_audio_norm[i],
            "delta_norm": round(abs(me_audio_norm[i] - other_audio_norm[i]), 4),
        })
    a_aff = audio_affinity(me_audio, other_audio)

    # Suggestions: artists the other has that I don't, ranked by genre overlap with my genres
    me_artist_ids = set(me_map.keys())
    suggestions = []
    for a in other_artists:
        if a.artist_id in me_artist_ids:
            continue
        a_genres = set([g for g in a.genres.split(",") if g]) if a.genres else set()
        overlap = len(me_genres & a_genres)
        suggestions.append({
            "id": a.artist_id,
            "name": a.artist_name,
            "overlap_genres": overlap,
        })
    suggestions.sort(key=lambda x: (x["overlap_genres"]), reverse=True)
    suggestions = suggestions[:10]

    # Icebreaker tracks: other user's tracks by shared artists
    other_tracks = list(session.exec(
        select(UserTrack).where(UserTrack.user_id == other_id, UserTrack.term == "medium").order_by(UserTrack.rank)
    ))
    shared_set = set(shared_ids)
    icebreaker = []
    for t in other_tracks:
        art_ids = [aid for aid in t.artist_ids.split(",") if aid]
        if shared_set & set(art_ids):
            icebreaker.append({
                "id": t.track_id,
                "name": t.track_name,
                "rank": t.rank,
                "artist_ids": art_ids,
            })
    icebreaker = icebreaker[:10]

    # Recent activity for the other user filtered to shared artists
    recent_rows = list(session.exec(select(RecentTrack).where(RecentTrack.user_id == other_id)))
    recent_activity = []
    for rt in recent_rows:
        arts = [aid for aid in (rt.artist_ids or "").split(",") if aid]
        if shared_set & set(arts):
            recent_activity.append({
                "track_id": rt.track_id,
                "track_name": rt.track_name,
                "played_at": rt.played_at,
                "artist_ids": arts,
            })
    recent_activity = recent_activity[:10]

    # Top-level metrics
    top = {
        "score": round(score({"artists": list(me_map.keys()), "genres": list(me_genres), "audio": me_audio},
                               {"artists": list(other_map.keys()), "genres": list(other_genres), "audio": other_audio}), 4),
        "shared_artists_count": len(shared_ids),
        "genre_overlap": round(jaccard(me_genres, other_genres), 4) if (me_genres or other_genres) else 0.0,
        "audio_affinity": round(a_aff, 4),
    }

    return {
        "summary": top,
        "shared_artists": shared,
        "shared_genres": shared_genres_ranked,
        "audio_breakdown": audio_breakdown,
        "suggestions_new_artists": suggestions,
        "icebreaker_tracks": icebreaker,
        "recent_activity": recent_activity,
    }
