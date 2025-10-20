from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User, Message as Msg, ConnectionRequest, UserSettings

router = APIRouter()


def _are_connected(session: Session, a: int, b: int) -> bool:
    q = select(ConnectionRequest).where(
        ConnectionRequest.status == "accepted",
        ((ConnectionRequest.from_user_id == a) & (ConnectionRequest.to_user_id == b))
        | ((ConnectionRequest.from_user_id == b) & (ConnectionRequest.to_user_id == a)),
    )
    return session.exec(q).first() is not None


@router.post("/messages")
def send_message(
    from_user_id: int = Query(...),
    to_user_id: int = Query(...),
    content: str = Query(...),
    session: Session = Depends(get_session),
):
    if not session.get(User, from_user_id) or not session.get(User, to_user_id):
        raise HTTPException(404, "User not found")
    # Ensure connection
    if not _are_connected(session, from_user_id, to_user_id):
        raise HTTPException(403, "Users are not connected")
    # Respect recipient settings
    to_settings = session.get(UserSettings, to_user_id)
    if to_settings and not to_settings.allow_messages:
        raise HTTPException(403, "Recipient does not allow messages")
    m = Msg(from_user_id=from_user_id, to_user_id=to_user_id, content=content)
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


@router.get("/messages/{user_id}")
def get_thread(user_id: int, other_id: int = Query(...), session: Session = Depends(get_session)):
    if not session.get(User, user_id) or not session.get(User, other_id):
        raise HTTPException(404, "User not found")
    q = select(Msg).where(
        ((Msg.from_user_id == user_id) & (Msg.to_user_id == other_id))
        | ((Msg.from_user_id == other_id) & (Msg.to_user_id == user_id))
    ).order_by(Msg.created_at)
    rows = session.exec(q).all()
    return rows


@router.get("/messages/conversations")
def list_conversations(user_id: int = Query(...), session: Session = Depends(get_session)):
    # naive: pull all messages involving user, group by other_id, pick last
    q = select(Msg).where((Msg.from_user_id == user_id) | (Msg.to_user_id == user_id)).order_by(Msg.created_at)
    rows = session.exec(q).all()
    last_by_other: dict[int, Msg] = {}
    for m in rows:
        other = m.to_user_id if m.from_user_id == user_id else m.from_user_id
        last_by_other[other] = m
    out = []
    for other_id, m in last_by_other.items():
        other_u = session.get(User, other_id)
        out.append({
            "user_id": other_id,
            "display_name": other_u.display_name if other_u else None,
            "last_message": m.content,
            "last_at": m.created_at.isoformat(),
        })
    return out

