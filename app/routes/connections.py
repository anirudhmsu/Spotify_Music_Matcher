from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User, ConnectionRequest, UserSettings

router = APIRouter()


@router.post("/connections/request")
def send_request(
    from_user_id: int = Query(...),
    to_user_id: int = Query(...),
    message: str | None = None,
    session: Session = Depends(get_session),
):
    if from_user_id == to_user_id:
        raise HTTPException(400, "Cannot connect to yourself")
    if not session.get(User, from_user_id) or not session.get(User, to_user_id):
        raise HTTPException(404, "User not found")
    # respect block list
    s_other = session.get(UserSettings, to_user_id)
    if s_other and s_other.blocked_user_ids:
        bl = {int(x) for x in s_other.blocked_user_ids.split(',') if x.strip().isdigit()}
        if from_user_id in bl:
            raise HTTPException(403, "You are blocked by this user")
    # upsert pending if exists
    existing = session.exec(
        select(ConnectionRequest).where(
            ConnectionRequest.from_user_id == from_user_id,
            ConnectionRequest.to_user_id == to_user_id,
            ConnectionRequest.status == "pending",
        )
    ).first()
    if existing:
        return {
            "id": existing.id,
            "from_user_id": existing.from_user_id,
            "to_user_id": existing.to_user_id,
            "status": existing.status,
            "message": existing.message,
            "created_at": existing.created_at
        }
    cr = ConnectionRequest(from_user_id=from_user_id, to_user_id=to_user_id, message=message or None)
    session.add(cr)
    session.commit()
    session.refresh(cr)
    return {
        "id": cr.id,
        "from_user_id": cr.from_user_id,
        "to_user_id": cr.to_user_id,
        "status": cr.status,
        "message": cr.message,
        "created_at": cr.created_at
    }


@router.get("/connections/pending")
def list_pending(user_id: int = Query(...), session: Session = Depends(get_session)):
    rows = session.exec(
        select(ConnectionRequest).where(ConnectionRequest.to_user_id == user_id, ConnectionRequest.status == "pending")
    ).all()
    return rows


def _get_req_or_404(session: Session, request_id: int) -> ConnectionRequest:
    cr = session.get(ConnectionRequest, request_id)
    if not cr:
        raise HTTPException(404, "Connection request not found")
    return cr


@router.post("/connections/{request_id}/accept")
def accept_request(request_id: int, session: Session = Depends(get_session)):
    cr = _get_req_or_404(session, request_id)
    cr.status = "accepted"
    session.add(cr)
    session.commit()
    session.refresh(cr)
    return {
        "id": cr.id,
        "from_user_id": cr.from_user_id,
        "to_user_id": cr.to_user_id,
        "status": cr.status,
        "message": cr.message,
        "created_at": cr.created_at
    }


@router.post("/connections/{request_id}/decline")
def decline_request(request_id: int, session: Session = Depends(get_session)):
    cr = _get_req_or_404(session, request_id)
    cr.status = "declined"
    session.add(cr)
    session.commit()
    session.refresh(cr)
    return {
        "id": cr.id,
        "from_user_id": cr.from_user_id,
        "to_user_id": cr.to_user_id,
        "status": cr.status,
        "message": cr.message,
        "created_at": cr.created_at
    }


@router.get("/connections")
def list_connections(user_id: int = Query(...), session: Session = Depends(get_session)):
    # accepted in either direction
    rows = session.exec(
        select(ConnectionRequest).where(
            ConnectionRequest.status == "accepted",
            (ConnectionRequest.from_user_id == user_id) | (ConnectionRequest.to_user_id == user_id),
        )
    ).all()
    out = []
    for r in rows:
        other_id = r.to_user_id if r.from_user_id == user_id else r.from_user_id
        other = session.get(User, other_id)
        out.append({
            "user_id": other.id,
            "display_name": other.display_name,
            "avatar_url": other.avatar_url,
        })
    return out

