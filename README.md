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
| Charts | Plotly, Recharts |
| Maps | Mapbox GL |
| Testing | pytest (backend), Vitest + React Testing Library (frontend) |

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- PostgreSQL 15+
- (Optional) Strava API credentials for OAuth sync

## Quick Start

Use the Makefile for unified start/stop commands:

```bash
make dev        # Start everything (DB + backend + frontend)
make stop       # Stop all services
make status     # Check what's running
make test       # Run test suite
```

Run `make help` for all available commands.

## Local Development

### 1. Clone the repo

```bash
git clone https://github.com/rriegel/strava-trends.git
cd strava-trends
```

### 2. Database

**Option A: Use Docker Compose (recommended)**

Start the test database (port 5433):

```bash
docker compose -f docker-compose.test.yml up -d
```

Then update `backend/.env` to match the test DB credentials:

```bash
DATABASE_URL=postgresql://test_user:test_password@localhost:5433/strava_trends_test
```

**Option B: Manual PostgreSQL setup**

```bash
createdb strava_trends
```

Or use Docker with matching credentials:

```bash
docker run -d --name strava-trends-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=strava_trends \
  -p 5433:5432 \
  postgres:15-alpine
```

Then ensure `backend/.env` has:

```bash
DATABASE_URL=postgresql://postgres:postgres@localhost/strava_trends
```

### 3. Backend

```bash
cd backend

# if encountering venv not found issues, reset it
rm -rf .venv

# Create virtual environment (use uv if python3-venv is not installed)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL (must match your DB credentials from step 2)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 4. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

The frontend is available at `http://localhost:3001`.

## Environment Variables

### Backend (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:***@localhost/strava_trends` |
| `STRAVA_CLIENT_ID` | Strava API OAuth client ID | — |
| `STRAVA_CLIENT_SECRET` | Strava API OAuth client secret | — |
| `STRAVA_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/auth/strava/callback` |
| `SECRET_KEY` | JWT signing key | `change-this-in-production` |
| `CORS_ORIGINS` | Allowed frontend origins | `["http://localhost:3001"]` |

## Running Tests

### Backend

Tests run against a dedicated PostgreSQL test database. Start it with:

```bash
docker compose -f docker-compose.test.yml up -d
```

Then run the test suite:

```bash
cd backend
source .venv/bin/activate
pytest
```

### Frontend

```bash
cd frontend
npm run test:run    # Single run
npm test            # Watch mode
```

## Stopping Services

Instead of manually hunting down processes with `lsof`, use:

```bash
make stop       # Stops backend, frontend, and database
make status     # Verify everything is shut down
```

If services are still lingering:

```bash
# Force kill by port
lsof -ti :8000 | xargs kill -9
lsof -ti :3001 | xargs kill -9

# Or use the clean target
make clean      # Stops services and removes containers
```

## Troubleshooting

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
├── docker-compose.test.yml   # Test database container
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
