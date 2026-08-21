.PHONY: dev stop backend frontend db db-test test clean help

# Default target
help:
	@echo "Strava Trends Development Commands"
	@echo ""
	@echo "  make dev        - Start all services (dev DB + backend + frontend)"
	@echo "  make stop       - Stop all running services"
	@echo "  make backend    - Start backend only (port 8000)"
	@echo "  make frontend   - Start frontend only (port 3001)"
	@echo "  make db         - Start dev database only (port 5432)"
	@echo "  make db-test    - Start test database only (port 5432)"
	@echo "  make test       - Run test suite (starts test DB automatically)"
	@echo "  make clean      - Stop services and remove all containers/volumes"
	@echo ""

# Start all services
dev: db backend frontend
	@echo "All services started:"
	@echo "  Frontend: http://localhost:3001"
	@echo "  Backend:  http://localhost:8000"
	@echo "  API Docs: http://localhost:8000/docs"

# Stop all services
stop:
	@echo "Stopping Strava Trends services..."
	@-pkill -f "uvicorn main:app" 2>/dev/null || true
	@-pkill -f "npm run dev" 2>/dev/null || true
	@-pkill -f "vite" 2>/dev/null || true
	@-lsof -ti :3001 2>/dev/null | xargs -r kill 2>/dev/null || true
	@-docker stop strava-trends-db 2>/dev/null || true
	@-docker stop strava-trends-test-db 2>/dev/null || true
	@echo "All services stopped"

# Start dev database
db:
	@echo "Starting dev database..."
	@docker compose up -d
	@echo "Dev database ready on port 5432"

# Start test database
db-test:
	@echo "Starting test database..."
	@docker compose -f docker-compose.test.yml up -d
	@echo "Test database ready on port 5432"

# Wait for dev database to be ready (uses healthcheck, not just pg_isready)
db-ready:
	@echo "Waiting for dev database to be ready..."
	@for i in $$(seq 1 30); do \
		HEALTH=$$(docker inspect --format='{{.State.Health.Status}}' strava-trends-db 2>/dev/null) && \
		if [ "$$HEALTH" = "healthy" ]; then \
			echo "Database is ready"; \
			exit 0; \
		fi; \
		echo "  Waiting... ($$i/30) [status: $$HEALTH]"; \
		sleep 1; \
	done; \
	echo "ERROR: Database failed to become healthy" && exit 1

# Wait for test database to be ready (uses healthcheck)
db-test-ready:
	@echo "Waiting for test database to be ready..."
	@for i in $$(seq 1 30); do \
		HEALTH=$$(docker inspect --format='{{.State.Health.Status}}' strava-trends-test-db 2>/dev/null) && \
		if [ "$$HEALTH" = "healthy" ]; then \
			echo "Test database is ready"; \
			exit 0; \
		fi; \
		echo "  Waiting... ($$i/30) [status: $$HEALTH]"; \
		sleep 1; \
	done; \
	echo "ERROR: Test database failed to become healthy" && exit 1

# Run database migrations with verification (dev DB)
migrate: db-ready
	@echo "Running database migrations..."
	@cd backend && . .venv/bin/activate && \
TABLE_EXISTS=$$(docker exec strava-trends-db psql -U postgres -d strava_trends -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'alembic_version');" | tr -d ' ') && \
TABLE_COUNT=$$(docker exec strava-trends-db psql -U postgres -d strava_trends -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ') && \
if [ "$$TABLE_EXISTS" = "f" ]; then \
	echo "  Fresh database (no alembic_version table). Running migrations..."; \
	alembic upgrade head; \
else \
	ALEMBIC_ROWS=$$(docker exec strava-trends-db psql -U postgres -d strava_trends -t -c "SELECT COUNT(*) FROM alembic_version;" | tr -d ' ') && \
	echo "  alembic_version rows: $$ALEMBIC_ROWS, tables: $$TABLE_COUNT" && \
	if [ "$$ALEMBIC_ROWS" = "0" ] && [ "$$TABLE_COUNT" -ge 8 ]; then \
		echo "  WARNING: Tables exist but alembic_version is empty (drift detected)"; \
		echo "  Resetting database to ensure consistency..."; \
		docker exec strava-trends-db psql -U postgres -d strava_trends -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
		alembic upgrade head && \
		echo "  Database reset and migrations applied"; \
	elif [ "$$ALEMBIC_ROWS" != "0" ] && [ "$$TABLE_COUNT" -lt 8 ]; then \
		echo "  alembic_version has rows but tables are missing. Resetting..."; \
		docker exec strava-trends-db psql -U postgres -d strava_trends -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" && \
		alembic upgrade head && \
		echo "  Migrations re-applied"; \
	elif [ "$$ALEMBIC_ROWS" = "0" ] && [ "$$TABLE_COUNT" -lt 8 ]; then \
		echo "  alembic_version exists but is empty. Running migrations..."; \
		alembic upgrade head; \
	else \
		echo "  Database state OK. Running migrations..."; \
		alembic upgrade head; \
	fi; \
fi && \
TABLE_COUNT=$$(docker exec strava-trends-db psql -U postgres -d strava_trends -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" | tr -d ' ') && \
echo "Database schema verified ($$TABLE_COUNT tables)"

# Seed dev user (idempotent)
seed-dev:
	@echo "Seeding dev user..."
	@docker exec strava-trends-db psql -U postgres -d strava_trends -c "\
		INSERT INTO users (id, strava_athlete_id, username, access_token, refresh_token, token_expires_at) \
		VALUES (1, 0, 'dev', 'dev_token', 'dev_token', NOW() + INTERVAL '1 year') \
		ON CONFLICT (id) DO NOTHING;" && \
	echo "Dev user seeded (or already exists)"

# Start backend
backend: migrate seed-dev
	@echo "Starting backend..."
	@cd backend && . .venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000 > /tmp/strava-trends-backend.log 2>&1 &
	@echo "Backend starting on port 8000 (logs: /tmp/strava-trends-backend.log)..."
	@sleep 3
	@ss -tlnp 2>/dev/null | grep ':8000 ' > /dev/null && echo "Backend is running" || (echo "Backend failed to start. Check /tmp/strava-trends-backend.log" && exit 1)

# Start frontend
frontend:
	@echo "Starting frontend..."
	@cd frontend && npm run dev > /tmp/strava-trends-frontend.log 2>&1 &
	@echo "Frontend starting on port 3001 (logs: /tmp/strava-trends-frontend.log)..."
	@sleep 3
	@ss -tlnp 2>/dev/null | grep ':3001 ' > /dev/null && echo "Frontend is running" || (echo "Frontend failed to start. Check /tmp/strava-trends-frontend.log" && exit 1)

# Run tests (uses test database)
test: db-test db-test-ready
	@echo "Running tests..."
	@cd backend && . .venv/bin/activate && pytest
	@cd frontend && npm run test:run

# Clean up everything
clean: stop
	@echo "Cleaning up containers and volumes..."
	@docker compose down -v 2>/dev/null || true
	@docker compose -f docker-compose.test.yml down -v 2>/dev/null || true

# Status check
status:
	@echo "Checking service status..."
	@echo ""
	@echo "Dev Database (strava-trends-db):"
	@docker ps --filter name=strava-trends-db --format "  {{.Status}}" 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "Test Database (strava-trends-test-db):"
	@docker ps --filter name=strava-trends-test-db --format "  {{.Status}}" 2>/dev/null || echo "  Not running"
	@echo ""
	@echo "Backend (port 8000):"
	@ss -tlnp 2>/dev/null | grep ':8000 ' || lsof -i :8000 2>/dev/null | grep LISTEN || echo "  Not running"
	@echo ""
	@echo "Frontend (port 3001):"
	@ss -tlnp 2>/dev/null | grep ':3001 ' || lsof -i :3001 2>/dev/null | grep LISTEN || echo "  Not running"
