import pytest
from sqlmodel import Session


def test_create_me_and_fetch(client):
    # Create a user directly in DB, then fetch via /me
    from app.db import engine
    from app.models.user import User

    with Session(engine) as s:
        u = User(spotify_id="test_spotify_id", display_name="Test User")
        s.add(u)
        s.commit()
        user_id = u.id

    resp = client.get(f"/me?user_id={user_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == user_id
    assert data["display_name"] == "Test User"
