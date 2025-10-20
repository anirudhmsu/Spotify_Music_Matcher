from sqlmodel import Session


def test_settings_and_blocklist_affect_matches(client):
    from app.db import engine
    from app.models.user import User
    from app.routes.settings import _parse_blocked

    # Seed two users
    with Session(engine) as s:
        u1 = User(spotify_id="s1", display_name="S One", country="US")
        u2 = User(spotify_id="s2", display_name="S Two", country="US")
        s.add(u1); s.add(u2); s.commit()
        me_id, other_id = u1.id, u2.id

    # Defaults: both public, no blocks
    r = client.get(f"/settings?user_id={me_id}")
    assert r.status_code == 200
    assert r.json()["is_public"] is True

    # Block other -> should not appear in matches
    rb = client.post(f"/users/{other_id}/block?user_id={me_id}")
    assert rb.status_code == 200
    assert other_id in rb.json()["blocked"]

    r = client.get(f"/matches?user_id={me_id}")
    assert r.status_code == 200
    assert all(m["user_id"] != other_id for m in r.json())

    # Unblock -> they can appear again (though score may be 0 without data)
    ru = client.delete(f"/users/{other_id}/block?user_id={me_id}")
    assert ru.status_code == 200
    assert other_id not in ru.json()["blocked"]

    # Make other user private -> should not appear
    up = client.put(f"/settings?user_id={other_id}", json={"is_public": False})
    assert up.status_code == 200
    r = client.get(f"/matches?user_id={me_id}")
    assert all(m["user_id"] != other_id for m in r.json())

