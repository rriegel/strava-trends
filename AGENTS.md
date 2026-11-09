# AGENTS.md — Strava Trends

Agent-facing project rules. Claude Code, Codex, and Hermes all read this file;
keep it in sync with reality — a stale rule here is worse than no rule.

**Privacy:** this repo must stay free of personal paths, hostnames, emails, and
secrets. Use placeholders (e.g. `/path/to/repo`, `$DATABASE_URL`) and environment
variables. Never commit runtime data (`backend/data/` is gitignored on purpose —
keep anything a feature writes at runtime under a gitignored path).

## Stack

- **Backend:** Python / FastAPI + SQLAlchemy + Alembic, Postgres, Makefile-driven
- **Frontend:** React + TypeScript + Vite, react-query v5, Mapbox GL
- **CI:** GitHub Actions — 3 gates (`backend_test`, `frontend_test`,
  `npm audit --omit=dev`). CI fires on PR and on push to `main` only, **not**
  on bare feature-branch pushes — don't wait for CI before opening the PR.

## Environment

- Postgres runs in Docker **on the dev machine**; there is no Docker where the
  agent runs — DBs are reached over TCP.
- **Two databases, never mix:**
  - dev: port 5432, db `strava_trends` — `backend/.env` points here
  - test: port 5433, db `strava_trends_test` — pytest ignores `.env` and always
    hits 5433 via conftest
- **Never use `backend/.venv` off-machine** — its shebangs/symlinks are
  machine-bound. Agent-side test runs use a throwaway venv instead (see
  Testing).
- `scipy` pin: use **Python 3.13**, not 3.14 (scipy==1.14.1 has no 3.14 wheel;
  uv silently falls back to a gfortran source build that fails). Applies to
  venvs AND `make setup`.

## Testing

- **Test-runner split:** the human runs backend pytest locally and pastes the
  failure list back; the agent does not auto-build a venv or run the suite
  unbidden. Hand over targeted commands (`pytest tests/test_X.py -x -q`).
  Agent-side full-suite runs are the explicitly-requested fallback.
- Frontend gates run freely agent-side: `npx tsc --noEmit`, `npx vitest run`,
  `npm run build` in `frontend/`.
- Frontend map tests need `frontend/.env` with `VITE_MAPBOX_TOKEN`; CI stubs it.
- **New tables must be added to BOTH drop-list blocks in
  `backend/tests/conftest.py`** (setup + teardown) or rows leak across
  tests/runs (PK violations, stale-row assertion failures).
- Tests that need a specific user id must create that user (+ pin sequences)
  or FK inserts fail. Post-auth: use the `sync_user`/`auth_headers` fixtures —
  endpoints derive identity from the JWT.
- **Local `auth_headers` overrides:** modules with their own user fixture MUST
  define a local `auth_headers` fixture overriding conftest's, or scoped
  endpoints 404/401 (token belongs to a different user).
- **Green tests ≠ applied migrations.** pytest builds tables from
  `Base.metadata` and never runs alembic. After adding a migration, run
  `alembic upgrade head` against the dev DB before manual testing.
- **Stub fixtures must grow with service→client calls.** A new method call on
  an injected client (e.g. sync service calling `get_activity_detail`) needs a
  matching `AsyncMock` in every fixture stubbing that client, or tests fail
  with `TypeError: ... can't be used in 'await' expression`. Router tests for
  new endpoints must include the guard fixtures (env vars, etc.) checked
  BEFORE the stub, or the guard error path fires first. Tests asserting a
  state side-effect must stub the data that effect derives from.

## Workflow

- Specs are written and approved before branching; feature branches only,
  merge via PR. PR descriptions summarize the commit stack.
- Playtest loop: agent implements + pushes; human tests on real hardware and
  reports symptoms. Verify reported bugs in code before reworking; commit
  hand-tuned deltas verbatim.
- Runtime data dirs are gitignored. Check `git status` before committing
  anything a feature wrote to disk.

## Data lifecycle

- Route derivation is synchronous inside the upload request — no async lag.
  Missing routes after upload = frontend cache problem, not timing.
- Upload dedupe key: user + source + source_id.
- Deleting an activity maintains its route: decrement `activity_count`,
  recompute aggregates over remaining linked activities; delete the route only
  when it was the last link. Any new deletion path must reuse that helper.
- Routes are user-scoped (migration 006): `polyline_hash` unique per
  `(user_id, polyline_hash)`. Never create Route rows without `user_id`.

## Backend conventions

- Raw values stay SI (meters, m/s) end-to-end. Pace converts server-side in
  the Trends APIs before regression math; distance/elevation convert
  client-side via `utils/format.ts` + `useUnits()`.
- Adding a new pace/elevation-like metric means updating BOTH sides:
  `AnalyticsEngine` metric sets/units in the backend, formatters/labels in the
  frontend.
- A unit flip is a user setting, NOT URL state; saving must invalidate every
  unit-bearing query family.

## Frontend conventions

- Filter/selection state lives in the URL (shareable).
- React Query global `staleTime: 5min`: every mutation must invalidate each
  derived query family it touches (see `UPLOAD_INVALIDATED_KEYS` for the
  pattern). Before wiring invalidation into a mutation, confirm the target
  page's data hook is actually a `useQuery` subscriber — a hand-rolled
  useState+useEffect hook silently ignores `invalidateQueries`.
- Account switch MUST clear the React Query cache (`queryClient.clear()` on
  logout + session adopt) or user A's cached queries render for user B.
- Param-change refetches use `placeholderData: keepPreviousData`; overlay
  status UI inside fixed-size cards (never inline blocks that shift layout).
- Per-entity arrays from the backend have independent lengths — never index
  one entity's array with a row index derived from another entity.
- Never render an in-progress working list from mutation data; keep working
  lists in component state.
- Multi-entity colors come from position in the canonical entity list, never
  id-hash.
- Map pages: container always-mounted; gate drawing on the real `load` event;
  viewport persistence via `utils/mapViewport.ts`; default centers come from
  the data's home area, never copied example coordinates.
- Auth tokens: access + refresh in localStorage, single shared-refresh-promise
  axios interceptor (queue concurrent 401s, one retry, refresh failure →
  clear + redirect to `/login?redirect=`). Preserve this in any auth refactor.
- Never assign `err.response.data.detail` to React state raw — FastAPI 422
  `detail` can be an array of validation objects; normalize via
  `extractErrorMessage` (pages/Login.tsx).
- Service-start scripts must poll a health endpoint, not `sleep N` + port
  check; after a failed/raced start, stop the old process before debugging
  (ghost processes serve stale code).

## Debugging discipline

- Verified diagnostics beat assumption: DB probe → API probe → real browser
  with screenshot before concluding anything is broken.
- For 500s with no visible traceback: reproduce outside uvicorn with a
  standalone script that imports the service directly.
- To reproduce user-reported request failures: run the server locally against
  the real dev DB and replay the exact payload.
