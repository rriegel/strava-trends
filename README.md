# Strava Trends

Fitness analytics platform that surfaces trends across activities over time. Strava's native analytics are limited — this app enables deeper analysis like comparing average pace across runs, overlaying multiple metrics, and grouping activities by distance, route, or effort level.

## Features

- **Data ingestion** via file upload (FIT/GPX/TCX) and Strava API sync
- **Metric trends** — pace, HR, cadence, elevation, HR/pace ratio, training load
- **Activity grouping** — by distance bucket, route (GPS clustering), effort zone, terrain
- **Visualizations** — time-series charts, calendar heatmap, route comparison, percentile bands

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, pandas |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Database | PostgreSQL 15 |
| Charts | Recharts |
| Maps | Mapbox GL |
| Testing | pytest (backend), Vitest + React Testing Library (frontend) |

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- Docker (runs both PostgreSQL containers — no local Postgres install needed)
- (Optional) Strava API credentials for OAuth sync
- (Optional) Mapbox access token for route map tiles

## The Two Databases

There are **two separate PostgreSQL databases**, and mixing them up is the #1 setup mistake:

| | Dev database | Test database |
|---|---|---|
| Port | **5432** | **5433** |
| Credentials | `postgres:postgres` | `test_user:test_password` |
| Database name | `strava_trends` | `strava_trends_test` |
| Compose file | `docker-compose.yml` | `docker-compose.test.yml` |
| Used by | The running app (`make dev` / `make backend`) | `make test` / pytest **only** |

**The rule:** `backend/.env` always points at the **dev database (5432)**. Never at the test database. The test database is fully self-managed — `make test` starts it, pytest resets its schema on every run, and pytest ignores `backend/.env` entirely (it uses its own hardcoded test-DB URL). Pointing your dev backend at 5433 will get you a database with no tables.

## Quick Start

```bash
# 1. Clone and configure
git clone https://github.com/rriegel/strava-trends.git
cd strava-trends
cp backend/.env.example backend/.env   # defaults match the dev DB below — no edits needed

# 2. Start everything (dev DB + migrations + dev user + backend + frontend)
make dev

# Frontend: http://localhost:3001
# API docs: http://localhost:8000/docs
```

Useful commands:

```bash
make dev        # Start everything (DB + backend + frontend)
make stop       # Stop all services
make status     # Check what's running
make test       # Run test suite (auto-starts the test DB)
make help       # All commands
```

## Local Development (step by step)

### 1. Database

**Option A: Docker Compose (recommended)** — matches the `backend/.env` defaults exactly:

```bash
make db          # equivalent to: docker compose up -d
```

This runs `postgres:15-alpine` on **port 5432** with user `postgres`, password `postgres`, database `strava_trends`. (These credentials are local-only — the container is not exposed beyond localhost.)

**Option B: Manual PostgreSQL / existing server**

Create a database and user, then point `backend/.env` at it:

```bash
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
```

Or spin up a matching disposable container yourself:

```bash
docker run -d --name strava-trends-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=strava_trends \
  -p 5432:5432 \
  postgres:15-alpine
```

> ⚠️ **Do not point `backend/.env` at port 5433** — that's the pytest database (`docker-compose.test.yml`). It exists only for `make test`, gets its tables dropped/recreated on every test run, and is normally empty. A dev backend pointed at it will fail with `relation "activities" does not exist`.

### 2. Backend

```bash
cd backend

# Create virtual environment (use uv if python3-venv is not installed)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env    # DATABASE_URL default matches the compose dev DB (port 5432)

# Run migrations (requires the dev DB from step 1 to be running)
alembic upgrade head

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

`make backend` (part of `make dev`) automates this: migrations, dev-user seed, and server start with logs at `/tmp/strava-trends-backend.log`.

A dev user (`id=1`, username `dev`) is seeded automatically by `make dev` / `make backend`.

### 3. Frontend

```bash
cd frontend

# Install dependencies — npm ci installs exactly from package-lock.json (known-good)
npm ci

# Start dev server
npm run dev
```

The frontend is available at `http://localhost:3001`.

Notes:

- **API access:** the Vite dev server proxies `/api/*` to `http://localhost:8000`, so no CORS configuration is needed in development.
- **Mapbox:** route-map tiles need a token — `cp .env.example .env` in `frontend/` and set `VITE_MAPBOX_TOKEN` (free at mapbox.com). Without it, map pages load but show no tile layer.
- If `npm ci` / `npm install` crashes with an arborist error like `Cannot read properties of null (reading 'edgesOut')` (an npm bug with this dependency set on some npm versions), retry with `npm install --legacy-peer-deps`.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string (**dev DB**, port 5432) | `postgresql://postgres:postgres@localhost:5432/strava_trends` |
| `STRAVA_CLIENT_ID` | Strava API OAuth client ID | — |
| `STRAVA_CLIENT_SECRET` | Strava API OAuth client secret | — |
| `STRAVA_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/auth/strava/callback` |
| `SECRET_KEY` | JWT signing key | `change-this-in-production` (dev only) |
| `CORS_ORIGINS` | Allowed frontend origins (only relevant without the Vite proxy) | `["http://localhost:5173","http://localhost:3000"]` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit | `100` |

### Frontend (`frontend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_MAPBOX_TOKEN` | Mapbox access token for route-map tiles | — |

## Running Tests

```bash
make test
```

starts the test database (port 5433) automatically, runs backend pytest, then frontend Vitest. Test databases are disposable: pytest drops and recreates all tables per test, and `backend/.env` is ignored — the suite always targets `strava_trends_test` on 5433.

Manual equivalent:

```bash
# Backend
docker compose -f docker-compose.test.yml up -d
cd backend && source .venv/bin/activate && pytest

# Frontend
cd frontend
npm run test:run    # Single run
npm test            # Watch mode
```

## Stopping Services

```bash
make stop       # Stops backend, frontend, and database containers
make status     # Verify what's still running
```

If services are still lingering:

```bash
# Force kill by port
lsof -ti :8000 | xargs kill -9
lsof -ti :3001 | xargs kill -9

# Or use the clean target
make clean      # Stops services and removes containers/volumes
```

## Troubleshooting

### Upload fails with `relation "activities" does not exist`

Your backend is pointed at the **test database** (or a fresh, unmigrated one). Check:

1. `backend/.env` — `DATABASE_URL` must reference port **5432** and database `strava_trends`
2. The dev DB is running: `make status` (or `docker ps`)
3. Migrations applied: `cd backend && alembic upgrade head`
4. Restart the backend after any `.env` change (uvicorn `--reload` does not reload env vars)

### Database migration issues

Migrations run automatically as part of `make backend` / `make dev`. The process detects and self-heals from drift:

- **Tables exist but alembic_version is empty** → drops schema and re-applies all migrations
- **alembic_version has rows but tables are missing** → clears tracking and re-applies migrations
- **Fresh database** → runs all migrations from scratch
- **Normal state** → applies only new migrations

If you still see issues, reset everything:

```bash
make clean
make dev
```

Note: resetting migrations clears all data and re-inserts the dev user (id=1, username='dev').

## Project Structure

```
strava-trends/
├── backend/
│   ├── alembic/          # Database migrations
│   ├── models/           # SQLAlchemy models
│   ├── routers/          # FastAPI route handlers
│   ├── services/         # Business logic (file parsing, analytics)
│   ├── tests/            # pytest test suite
│   ├── config.py         # Settings / env vars
│   ├── database.py       # DB connection setup
│   └── main.py           # FastAPI app entrypoint
├── frontend/
│   ├── src/
│   │   ├── api/          # API client (axios)
│   │   ├── components/   # React components
│   │   ├── hooks/        # Custom React hooks
│   │   ├── pages/        # Route-level page components
│   │   ├── types/        # TypeScript type definitions
│   │   └── utils/        # Shared utilities
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml        # Dev database container (port 5432)
├── docker-compose.test.yml   # Test database container (port 5433)
└── README.md
```

## Data Sources

| Source | Status | Notes |
|--------|--------|-------|
| File Upload (FIT/GPX/TCX) | ✅ Available | Works for any device |
| Strava API | ✅ Available | OAuth + webhooks |
| Garmin Connect | 🔒 Blocked | Developer program paused (March 2026) |

Activities are deduplicated across sources by matching start time + distance + duration.

## License

Private — not for distribution.