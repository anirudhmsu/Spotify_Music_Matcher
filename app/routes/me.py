# app/routes/me.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.db import get_session
from app.models.user import User
from app.models.music import RecentTrack

router = APIRouter()

@router.get("")
def get_me(user_id: int = Query(...), session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    return u


@router.get("/recent")
def get_recent(user_id: int = Query(...), session: Session = Depends(get_session)):
    rows = session.exec(select(RecentTrack).where(RecentTrack.user_id == user_id)).all()
    return rows
