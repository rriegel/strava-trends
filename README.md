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

## Local Development

### 1. Clone the repo

```bash
git clone https://github.com/rriegel/strava-trends.git
cd strava-trends
```

### 2. Database

Set up a PostgreSQL database:

```bash
createdb strava_trends
```

Or use Docker:

```bash
docker run -d --name strava-trends-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=strava_trends \
  -p 5432:5432 \
  postgres:15-alpine
```

### 3. Backend

```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL and Strava credentials

# Run database migrations
alembic upgrade head

# Start the server
uvicorn main:app --reload --port 8000
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

The frontend is available at `http://localhost:5173`.

## Environment Variables

### Backend (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:***@localhost/strava_trends` |
| `STRAVA_CLIENT_ID` | Strava API OAuth client ID | — |
| `STRAVA_CLIENT_SECRET` | Strava API OAuth client secret | — |
| `STRAVA_REDIRECT_URI` | OAuth callback URL | `http://localhost:8000/auth/strava/callback` |
| `SECRET_KEY` | JWT signing key | `change-this-in-production` |
| `CORS_ORIGINS` | Allowed frontend origins | `["http://localhost:5173"]` |

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
