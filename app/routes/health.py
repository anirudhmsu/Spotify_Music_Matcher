from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def root():
    return {
        "name": "Spotify Match POC",
        "status": "ok",
        "docs": "/docs",
        "endpoints": [
            "/auth/login",
            "/callback",
            "/ingest/spotify?user_id=...",
            "/me?user_id=...",
            "/matches?user_id=...",
            "/healthz",
        ],
    }


@router.get("/healthz")
def healthz():
    return {"status": "ok"}

