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

- Python 3.11+ (or [uv](https://docs.astral.sh/uv/) — used automatically if installed)
- Node.js 18+ and npm
- Docker (runs both PostgreSQL containers — no local Postgres install needed)
- (Optional) Strava API credentials for OAuth sync
- (Optional) Mapbox access token for route map tiles

## The Two Databases

There are **two separate PostgreSQL databases**:

| | Dev database | Test database |
|---|---|---|
| Port | **5432** | **5433** |
| Credentials | `postgres:postgres` | `test_user:test_password` |
| Database name | `strava_trends` | `strava_trends_test` |
| Compose file | `docker-compose.yml` | `docker-compose.test.yml` |
| Used by | The running app (`make dev` / `make backend`) | `make test` / pytest **only** |

**The rule:** `backend/.env` always points at the **dev database (5432)**. The test database is fully self-managed - `make test` starts it, pytest resets its schema on every run, and pytest ignores `backend/.env`

## Quick Start

```bash
git clone https://github.com/rriegel/strava-trends.git
cd strava-trends
make setup   # one-time: venv, deps, .env files, npm ci
make dev     # start dev DB + backend + frontend
```

Frontend: http://localhost:3001 · API docs: http://localhost:8000/docs

Everyday commands: `make dev` (start) · `make stop` · `make status` · `make test`. Run `make help` for everything.

## Local Development

### 1. Database

`make dev` starts the dev database via `docker compose` (`postgres:15-alpine`, port **5432**, user `postgres`, password `postgres`, database `strava_trends`). The `.env` defaults match it exactly.

Using an existing PostgreSQL server instead? Point `backend/.env` at it:

```
DATABASE_URL=postgresql://<user>:<password>@<host>:<port>/<dbname>
```

### 2. What `make setup` does

`make setup` (first run only, safe to re-run — never overwrites an existing `.env`) performs all bootstrap steps. Nothing in the Makefile assumes you've done more than clone the repo.

**Backend** — created `backend/.venv` (with `uv` if available, otherwise `python3 -m venv`), installed `requirements.txt` into it, and copied `.env.example` → `.env`. The `DATABASE_URL` default targets the compose dev DB; `SECRET_KEY` is fine for local dev but must be changed for any real deployment.

**Frontend** — ran `npm ci` (installs exactly what `package-lock.json` pins) and copied `.env.example` → `.env`. Set `VITE_MAPBOX_TOKEN` in `frontend/.env` (free at mapbox.com) for route-map tiles — without it, map pages load but show no tile layer. No API URL config is needed: the Vite dev server proxies `/api/*` to `http://localhost:8000`, so CORS never enters the picture in development.

Prefer doing it by hand? The equivalent is documented in `backend/.env.example` and `frontend/.env.example` comments — the Makefile is the source of truth for the exact commands.

### 3. Running services

```bash
make dev        # db + backend + frontend
make backend    # backend only (migrations + dev-user seed + uvicorn)
make frontend   # frontend only
```

Logs: `/tmp/strava-trends-backend.log`, `/tmp/strava-trends-frontend.log`. A dev user (`id=1`, username `dev`) is seeded automatically. `make backend` runs migrations and self-heals schema drift before starting.

## Running Tests

```bash
make test
```

Starts the test database (port 5433) automatically, runs backend pytest, then frontend Vitest. Test databases are disposable: pytest drops and recreates all tables per test, and `backend/.env` is ignored — the suite always targets `strava_trends_test` on 5433.

Frontend tests in watch mode (not covered by `make test`):

```bash
cd frontend
npm run test:run    # Single run
npm test            # Watch mode
```

## Stopping Services

```bash
make stop       # Stops backend, frontend, and database containers
make status     # Verify what's still running
make clean      # Stops services AND removes containers/volumes
```

## Troubleshooting

### Upload fails with `relation "activities" does not exist`

Your backend is pointed at the **test database** (or a fresh, unmigrated one). Check:

1. `backend/.env` — `DATABASE_URL` must reference port **5432** and database `strava_trends`
2. The dev DB is running: `make status` (or `docker ps`)
3. Migrations applied: `cd backend && . .venv/bin/activate && alembic upgrade head`
4. Restart the backend after any `.env` change (uvicorn `--reload` does not reload env vars)

### Other database issues

Migrations run automatically in `make dev` / `make backend` and self-heal schema drift. If anything is still broken:

```bash
make clean && make dev
```

Note: this clears all data and re-inserts the dev user (id=1, username='dev').

### `npm ci` fails with arborist error (`Cannot read properties of null (reading 'edgesOut')`)

An npm bug with this dependency set on some npm versions. Retry with:

```bash
cd frontend && npm install --legacy-peer-deps
```

## Data Sources

| Source | Status | Notes |
|--------|--------|-------|
| File Upload (FIT/GPX/TCX) | Available | Works for any device |
| Strava API | Available | OAuth + webhooks |
| Garmin Connect | Blocked | Developer program paused (March 2026) |

Activities are deduplicated across sources by matching start time + distance + duration.

## License

Private — not for distribution.