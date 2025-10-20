Spotify Music Matching (Backend)

Spotify Music Matching is a Hobby Project of mine, where people can match with eachother based on their music taste, sort of like a Social Media for people, to make friends based on their Music Taste. The APP is currently on initial stages and is open for contribution. (Original)


What This Is
- FastAPI backend for Spotify-based social matching: OAuth, data ingest (top artists/tracks + audio features), similarity scoring, and a “people like me” leaderboard.

Stack
- API: FastAPI + Uvicorn
- DB/ORM: SQLModel (SQLite by default; Postgres-ready)
- OAuth: Authlib (Spotify Authorization Code)
- HTTP: httpx (async)
- Tests: pytest + httpx ASGI transport

Prereqs
- Python 3.11+
- Spotify Developer App with Redirect URI set to `http://localhost:8000/auth/callback`

Configuration
- Copy `.env.example` to `.env` and fill values:
  - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
  - `SPOTIFY_REDIRECT_URI` (usually `http://localhost:8000/auth/callback`)
  - `DATABASE_URL` (defaults to `sqlite:///./dev.db` if unset)

Install & Run
- Using Makefile (recommended):
  - `make setup`          # creates venv and installs deps
  - `make run`            # starts server at http://localhost:8000
- Manual:
  - `python -m venv .venv && source .venv/bin/activate`
  - `pip install -r requirements.txt`
  - `uvicorn app.main:app --reload --port 8000`

OAuth Flow (First Login)
- Visit `http://localhost:8000/auth/login`
- Approve Spotify consent → callback stores tokens and redirects to `/ingest/spotify?user_id=...` to fetch your data

Core Endpoints
- `GET /auth/login`: Start Spotify OAuth
- `GET /auth/callback`: Finish OAuth; upsert user + tokens
- `GET /ingest/spotify?user_id=ID`: Fetch top artists/tracks (short/medium/long) and audio centroid
- `GET /ingest/spotify/recent?user_id=ID`: Fetch and store recently played tracks
- `GET /me?user_id=ID`: Get user record
- `GET /me/recent?user_id=ID`: Get recent listening activity
- `GET /matches?user_id=ID`: Ranked matches with scores and summary signals
  - Adds: `shared_artists_count`, `genre_overlap`, `audio_affinity`
- `GET /matches/explain?user_id=ID&other_id=ID`: Explain a specific match with details
  - `summary`: score, overlaps, audio affinity
  - `shared_artists`: list with names and ranks for both users
  - `shared_genres`: overlapping genres with counts per user
  - `audio_breakdown`: per-dimension raw/normalized values and deltas
  - `suggestions_new_artists`: other user’s artists you may like (ranked by genre overlap)
  - `icebreaker_tracks`: other user’s top tracks by shared artists
  - `recent_activity`: other user’s recent plays by shared artists
- `GET /settings?user_id=ID`: Get privacy settings
- `PUT /settings?user_id=ID`: Update privacy settings
- `GET /users/blocked?user_id=ID`: List blocked user IDs
- `POST /users/{target_id}/block?user_id=ID`: Block a user
- `DELETE /users/{target_id}/block?user_id=ID`: Unblock a user
- `POST /connections/request?from_user_id=A&to_user_id=B` Send a connection request
- `GET /connections/pending?user_id=ID`: Pending incoming requests
- `POST /connections/{request_id}/accept|decline`: Accept/decline a request
- `GET /connections?user_id=ID`: List accepted connections
- `POST /messages?from_user_id=A&to_user_id=B&content=...`: Send message to a connection
- `GET /messages/{user_id}?other_id=ID`: Get a conversation thread
- `GET /messages/conversations?user_id=ID`: List conversations with last message

Testing
- `make test`  # uses a temporary SQLite file DB (`test.db`)
- What’s covered:
  - Scoring math sanity (`tests/test_scoring.py`)
  - Basic user read (`tests/test_auth_flow.py`)
  - Matches endpoint with seeded users (`tests/test_matches.py`)

Project Layout
- `app/main.py`: App factory, routers, CORS
- `app/db.py`: Engine, session, metadata init
- `app/models/user.py`: `User`, `SpotifyToken`
- `app/models/music.py`: `UserArtist`, `UserTrack`, `UserAudioProfile`
- `app/routes/oauth.py`: Spotify OAuth login/callback
- `app/routes/ingest.py`: Pulls top artists/tracks; builds audio centroid
- `app/routes/matches.py`: Leaderboard of similar users
- `app/routes/settings.py`: Privacy settings and blocklist endpoints
- `app/routes/connections.py`: Connection request workflow
- `app/routes/messages.py`: Messaging between connected users
- `app/services/spotify.py`: Token refresh + Spotify API calls
- `app/services/scoring.py`: Similarity function

Next Steps
- Explanations per match (shared artists, BPM window)
- Filters (same country, min overlap)
- Postgres + pgvector for ANN candidate preselect
- Minimal React/Next.js frontend hitting these endpoints

Changes in this iteration
- Audio feature normalization for fairer similarity scoring.
- Safer ORM deletes in ingest and improved token refresh errors.
- Enriched `/matches` response with helpful summary fields.
- New explainability endpoint `/matches/explain` with actionable insights.
