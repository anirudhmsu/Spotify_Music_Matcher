from sqlmodel import Session


def test_explain_endpoint_returns_breakdown(client):
    from app.db import engine
    from app.models.user import User
    from app.models.music import UserArtist, UserAudioProfile, UserTrack

    with Session(engine) as s:
        # Seed users
        u1 = User(spotify_id="e1", display_name="Explainer One")
        u2 = User(spotify_id="e2", display_name="Explainer Two")
        s.add(u1); s.add(u2); s.commit()

        # Artists (medium): overlap on a2
        s.add(UserArtist(user_id=u1.id, term="medium", artist_id="a1", artist_name="A1", genres="techno,house", popularity=50, rank=1))
        s.add(UserArtist(user_id=u1.id, term="medium", artist_id="a2", artist_name="A2", genres="house", popularity=40, rank=2))
        s.add(UserArtist(user_id=u2.id, term="medium", artist_id="a2", artist_name="A2", genres="house", popularity=40, rank=1))
        s.add(UserArtist(user_id=u2.id, term="medium", artist_id="a3", artist_name="A3", genres="trance", popularity=30, rank=2))

        # Tracks for icebreakers
        s.add(UserTrack(user_id=u2.id, term="medium", track_id="t1", track_name="Song 1", artist_ids="a2", popularity=50, rank=1))
        s.add(UserTrack(user_id=u2.id, term="medium", track_id="t2", track_name="Song 2", artist_ids="a3", popularity=40, rank=2))

        # Audio profiles
        s.add(UserAudioProfile(user_id=u1.id, tempo=120, energy=0.8, valence=0.6, danceability=0.7, acousticness=0.1, loudness=-6))
        s.add(UserAudioProfile(user_id=u2.id, tempo=122, energy=0.78, valence=0.62, danceability=0.69, acousticness=0.12, loudness=-6.5))
        s.commit()
        # Capture IDs before session closes to avoid DetachedInstanceError on expired attrs
        u1_id = u1.id
        u2_id = u2.id

    r = client.get(f"/matches/explain?user_id={u1_id}&other_id={u2_id}")
    assert r.status_code == 200
    data = r.json()
    assert set(data.keys()) == {
        "summary",
        "shared_artists",
        "shared_genres",
        "audio_breakdown",
        "suggestions_new_artists",
        "icebreaker_tracks",
        "recent_activity",
    }
    assert data["summary"]["shared_artists_count"] == 1
    assert any(itm["id"] == "t1" for itm in data["icebreaker_tracks"])  # a2 track shows up
    assert data["summary"]["score"] > 0
