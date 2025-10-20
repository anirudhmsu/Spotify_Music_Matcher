from sqlmodel import Session


def test_matches_filters_and_pagination(client):
    from app.db import engine
    from app.models.user import User
    from app.models.music import UserArtist, UserAudioProfile

    with Session(engine) as s:
        me = User(spotify_id="f_me", display_name="Filter Me", country="US")
        u1 = User(spotify_id="f1", display_name="Filter One", country="US")
        u2 = User(spotify_id="f2", display_name="Filter Two", country="GB")
        s.add(me); s.add(u1); s.add(u2); s.commit()
        me_id, u1_id, u2_id = me.id, u1.id, u2.id

        # Seed artists so that u1 shares a genre/artist with me; u2 does not
        s.add(UserArtist(user_id=me_id, term="medium", artist_id="a1", artist_name="A1", genres="techno", popularity=10, rank=1))
        s.add(UserArtist(user_id=u1_id, term="medium", artist_id="a1", artist_name="A1", genres="techno", popularity=10, rank=1))
        s.add(UserArtist(user_id=u2_id, term="medium", artist_id="b1", artist_name="B1", genres="jazz", popularity=10, rank=1))
        s.add(UserAudioProfile(user_id=me_id, tempo=120, energy=0.5, valence=0.5, danceability=0.5, acousticness=0.5, loudness=-10))
        s.add(UserAudioProfile(user_id=u1_id, tempo=121, energy=0.5, valence=0.5, danceability=0.5, acousticness=0.5, loudness=-10))
        s.add(UserAudioProfile(user_id=u2_id, tempo=180, energy=0.1, valence=0.2, danceability=0.2, acousticness=0.9, loudness=-30))
        s.commit()

    # Filter by country
    r = client.get(f"/matches?user_id={me_id}&country=US")
    users = [m["user_id"] for m in r.json()]
    assert u1_id in users
    assert u2_id not in users

    # Require genre
    r = client.get(f"/matches?user_id={me_id}&has_genres=techno")
    users = [m["user_id"] for m in r.json()]
    assert u1_id in users
    assert u2_id not in users

    # Min shared artists
    r = client.get(f"/matches?user_id={me_id}&min_shared_artists=1")
    users = [m["user_id"] for m in r.json()]
    assert u1_id in users
    assert u2_id not in users

    # Pagination: limit 1, cursor 1 should skip first
    r0 = client.get(f"/matches?user_id={me_id}&limit=1").json()
    r1 = client.get(f"/matches?user_id={me_id}&limit=1&cursor=1").json()
    if r0 and r1:
        assert r0[0]["user_id"] != r1[0]["user_id"]

