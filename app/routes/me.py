# app/routes/me.py
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session
from app.db import get_session
from app.models.user import User

router = APIRouter()

@router.get("")
def get_me(user_id: int = Query(...), session: Session = Depends(get_session)):
    u = session.get(User, user_id)
    return u
