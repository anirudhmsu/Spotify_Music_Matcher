from sqlmodel import Session


def test_matches_endpoint_scores_other_users(client):
    from app.db import engine
    from app.models.user import User
    from app.models.music import UserArtist, UserAudioProfile

    with Session(engine) as s:
        # Create two users
        u1 = User(spotify_id="u1", display_name="Alpha")
        u2 = User(spotify_id="u2", display_name="Beta")
        s.add(u1); s.add(u2); s.commit()

        # Add overlapping artists (medium term)
        s.add(UserArtist(user_id=u1.id, term="medium", artist_id="a1", artist_name="A1", genres="techno,house", popularity=50, rank=1))
        s.add(UserArtist(user_id=u1.id, term="medium", artist_id="a2", artist_name="A2", genres="house", popularity=40, rank=2))
        s.add(UserArtist(user_id=u2.id, term="medium", artist_id="a2", artist_name="A2", genres="house", popularity=40, rank=1))
        s.add(UserArtist(user_id=u2.id, term="medium", artist_id="a3", artist_name="A3", genres="trance", popularity=30, rank=2))

        # Audio profiles
        s.add(UserAudioProfile(user_id=u1.id, tempo=120, energy=0.8, valence=0.6, danceability=0.7, acousticness=0.1, loudness=-6))
        s.add(UserAudioProfile(user_id=u2.id, tempo=122, energy=0.78, valence=0.62, danceability=0.69, acousticness=0.12, loudness=-6.5))
        s.commit()

        me_id = u1.id

    r = client.get(f"/matches?user_id={me_id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
    assert data[0]["user_id"] != me_id
    assert data[0]["score"] > 0

