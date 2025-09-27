# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from app.db import init_db
from dotenv import load_dotenv
import os

# Load env early so providers read correct values
load_dotenv()

from app.routes import oauth, ingest, matches, me
from app.routes import health

app = FastAPI(title="Spotify Match POC")

@app.on_event("startup")
def startup():
    init_db()

app.include_router(oauth.router, prefix="/auth", tags=["auth"])
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(me.router, prefix="/me", tags=["me"])
app.include_router(matches.router, prefix="/matches", tags=["matches"])
app.include_router(health.router, tags=["health"])  # adds / and /healthz

# Allow local frontends during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware for OAuth state/PKCE
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("APP_SECRET", "dev-secret"),
    same_site="lax",
    https_only=False,
    session_cookie="sm_session",
)

# Optional: support root-level callback path /callback to match
# SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
app.add_api_route("/callback", oauth.auth_callback, methods=["GET"]) 
