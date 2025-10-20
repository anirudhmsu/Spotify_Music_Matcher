from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlmodel import Session
from app.db import get_session
from app.models.user import User, UserSettings

router = APIRouter()


def _get_or_create_settings(user_id: int, session: Session) -> UserSettings:
    s = session.get(UserSettings, user_id)
    if s:
        return s
    # ensure user exists
    if not session.get(User, user_id):
        raise HTTPException(404, "User not found")
    s = UserSettings(user_id=user_id)
    session.add(s)
    session.commit()
    return s


class SettingsUpdate(BaseModel):
    is_public: bool | None = None
    allow_messages: bool | None = None
    show_country: bool | None = None


@router.get("/settings")
def get_settings(user_id: int = Query(...), session: Session = Depends(get_session)):
    s = _get_or_create_settings(user_id, session)
    return {
        "user_id": s.user_id,
        "is_public": s.is_public,
        "allow_messages": s.allow_messages,
        "show_country": s.show_country,
        "blocked_user_ids": s.blocked_user_ids
    }


@router.put("/settings")
def update_settings(
    payload: SettingsUpdate,
    user_id: int = Query(...),
    session: Session = Depends(get_session),
):
    s = _get_or_create_settings(user_id, session)
    if payload.is_public is not None:
        s.is_public = payload.is_public
    if payload.allow_messages is not None:
        s.allow_messages = payload.allow_messages
    if payload.show_country is not None:
        s.show_country = payload.show_country
    session.add(s)
    session.commit()
    session.refresh(s)
    return {
        "user_id": s.user_id,
        "is_public": s.is_public,
        "allow_messages": s.allow_messages,
        "show_country": s.show_country,
        "blocked_user_ids": s.blocked_user_ids
    }


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


@router.get("/users/blocked")
def list_blocked(user_id: int = Query(...), session: Session = Depends(get_session)):
    s = _get_or_create_settings(user_id, session)
    return sorted(list(_parse_blocked(s.blocked_user_ids)))


@router.post("/users/{target_id}/block")
def block_user(target_id: int, user_id: int = Query(...), session: Session = Depends(get_session)):
    if not session.get(User, user_id) or not session.get(User, target_id):
        raise HTTPException(404, "User not found")
    s = _get_or_create_settings(user_id, session)
    blocked = _parse_blocked(s.blocked_user_ids)
    blocked.add(target_id)
    s.blocked_user_ids = ",".join(str(i) for i in sorted(blocked)) if blocked else None
    session.add(s)
    session.commit()
    return {"ok": True, "blocked": sorted(list(blocked))}


@router.delete("/users/{target_id}/block")
def unblock_user(target_id: int, user_id: int = Query(...), session: Session = Depends(get_session)):
    if not session.get(User, user_id) or not session.get(User, target_id):
        raise HTTPException(404, "User not found")
    s = _get_or_create_settings(user_id, session)
    blocked = _parse_blocked(s.blocked_user_ids)
    if target_id in blocked:
        blocked.remove(target_id)
    s.blocked_user_ids = ",".join(str(i) for i in sorted(blocked)) if blocked else None
    session.add(s)
    session.commit()
    return {"ok": True, "blocked": sorted(list(blocked))}

