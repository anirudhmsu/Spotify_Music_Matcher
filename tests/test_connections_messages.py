from sqlmodel import Session


def test_connections_flow_and_messaging(client):
    from app.db import engine
    from app.models.user import User

    with Session(engine) as s:
        a = User(spotify_id="c1", display_name="Conn A")
        b = User(spotify_id="c2", display_name="Conn B")
        s.add(a); s.add(b); s.commit()
        a_id, b_id = a.id, b.id

    # Send request from A to B
    r = client.post(f"/connections/request?from_user_id={a_id}&to_user_id={b_id}&message=hi")
    assert r.status_code == 200
    req = r.json()
    assert req["status"] == "pending"

    # B sees pending
    pend = client.get(f"/connections/pending?user_id={b_id}").json()
    assert len(pend) == 1

    # Accept
    rid = req["id"]
    acc = client.post(f"/connections/{rid}/accept")
    assert acc.status_code == 200
    assert acc.json()["status"] == "accepted"

    # List connections for A
    conns = client.get(f"/connections?user_id={a_id}").json()
    assert any(c["user_id"] == b_id for c in conns)

    # Messaging now allowed
    sm = client.post(f"/messages?from_user_id={a_id}&to_user_id={b_id}&content=hello")
    assert sm.status_code == 200
    # Thread should include the message
    th = client.get(f"/messages/{a_id}?other_id={b_id}").json()
    assert any(m["content"] == "hello" for m in th)

