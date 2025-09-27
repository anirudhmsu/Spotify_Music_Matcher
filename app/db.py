# app/db.py
from sqlmodel import SQLModel, create_engine, Session
import os

engine = create_engine(os.getenv("DATABASE_URL", "sqlite:///./dev.db"), echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as s:
        yield s
