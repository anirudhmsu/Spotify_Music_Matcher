# app/models/user.py
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime, UTC

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    spotify_id: str = Field(index=True, unique=True)
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    country: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

class SpotifyToken(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    access_token: str
    refresh_token: str
    expires_at: datetime
