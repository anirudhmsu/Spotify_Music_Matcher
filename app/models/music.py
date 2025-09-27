from sqlmodel import SQLModel, Field


class UserArtist(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    term: str = Field(primary_key=True)  # short|medium|long
    artist_id: str = Field(primary_key=True)
    artist_name: str
    genres: str  # CSV for POC (can move to JSON)
    popularity: int
    rank: int


class UserTrack(SQLModel, table=True):
    user_id: int = Field(foreign_key="user.id", primary_key=True)
    term: str = Field(primary_key=True)
    track_id: str = Field(primary_key=True)
    track_name: str
    artist_ids: str
    popularity: int
    rank: int


class UserAudioProfile(SQLModel, table=True):
    user_id: int = Field(primary_key=True, foreign_key="user.id")
    tempo: float
    energy: float
    valence: float
    danceability: float
    acousticness: float
    loudness: float

