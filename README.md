# Mandate Retry Sequencer

AI-assisted retry sequencing for failed payment mandates — a FastAPI backend
with a LangGraph-driven decision workflow, a React + Vite frontend, and a
PostgreSQL database.

- **Frontend:** `frontend/` — React 19 + TypeScript + Vite, built and served as static files by Nginx.
- **Backend:** `backend/` — FastAPI + Uvicorn, SQLAlchemy 2.x, Alembic migrations, APScheduler background jobs.
- **Database:** PostgreSQL.

This README covers running the whole stack with **Docker Compose**. For
running each service directly on your machine instead (no Docker), see
[Running without Docker](#running-without-docker) near the bottom.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and [Docker Compose v2](https://docs.docker.com/compose/install/) (`docker compose version` should work — it ships with Docker Desktop)
- A [Groq API key](https://console.groq.com) if you want AI-enriched decisions (optional — the app works fully on deterministic policy without one)
- A [Razorpay](https://razorpay.com) test-mode key pair if you want real payment-gateway integration (optional — the app runs in demo mode without one)

Nothing else needs to be installed locally — Node, Python, and Postgres all run inside containers.

---

## 1. Configure environment variables

Docker Compose reads a `.env` file in this directory to fill in
`docker-compose.yml`. Copy the template and fill in what you have:

```bash
cp .env.example .env
```

Open `.env` and set at minimum:
- `POSTGRES_PASSWORD` — pick any password for the local database container
- `GROQ_API_KEY` — optional, leave blank to run deterministic-only
- `RAZORPAY_KEY_ID` / `RAZORPAY_KEY_SECRET` — optional, leave blank to run in demo mode

See [Environment variables reference](#environment-variables-reference) below for what every variable does.

## 2. Build the images

```bash
docker compose build
```

## 3. Start the stack

```bash
docker compose up
```

Add `-d` to run in the background: `docker compose up -d`.

First startup will take a few seconds longer than later ones — the backend
waits for Postgres to become healthy, then creates the database schema
before it starts serving requests (see [`backend/init_db.py`](backend/init_db.py)).

## 4. Stop the stack

```bash
docker compose down
```

This stops and removes the containers but **keeps your database data**
(it lives in the `postgres_data` named volume). To also wipe the database:

```bash
docker compose down -v
```

## 5. View logs

```bash
docker compose logs -f            # all services
docker compose logs -f backend    # just the backend
docker compose logs -f frontend
docker compose logs -f postgres
```

## 6. Rebuild after code changes

Docker images are built once — they don't pick up source changes
automatically. After editing backend or frontend code:

```bash
docker compose up --build
```

To rebuild just one service: `docker compose build backend` (or `frontend`), then `docker compose up -d`.

---

## Accessing the app

| What | URL |
|---|---|
| Frontend | http://localhost:3000 |
| Backend API root | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| OpenAPI schema | http://localhost:8000/openapi.json |
| Postgres (for `psql` / a GUI client) | `localhost:5432` |

The frontend container's Nginx proxies its own `/api/` and `/health` requests
to the backend container internally (see `frontend/nginx.conf`), so the
frontend works correctly from `http://localhost:3000` without needing to
know the backend's address separately.

---

## Docker architecture

```
                 ┌──────────────────────┐
   :3000  ─────► │   frontend (Nginx)   │
                 │  serves the built    │
                 │  React SPA; proxies  │───┐
                 └──────────────────────┘   │ /api/*, /health
                                             ▼
                 ┌──────────────────────┐
   :8000  ─────► │   backend (Uvicorn)  │
                 │   FastAPI + APScheduler│
                 └──────────┬───────────┘
                             │ DATABASE_URL (internal, "postgres" hostname)
                             ▼
                 ┌──────────────────────┐
   :5432  ─────► │      postgres        │
                 │  (named volume:      │
                 │   postgres_data)     │
                 └──────────────────────┘
```

All three services share a single Docker network (`app-network`) and reach
each other by service name (`backend`, `postgres`) — only `frontend` needs to
know about `backend`, and only from inside the container (via Nginx), not
from the browser.

- `postgres` has a `pg_isready` healthcheck; `backend` won't start until it reports healthy.
- `backend` has an HTTP healthcheck against `GET /`; `frontend` won't start until it reports healthy.
- `backend`'s database schema is created automatically on first boot — see [Database schema on first boot](#database-schema-on-first-boot).

---

## Environment variables reference

Set these in `.env` at the repo root (Docker Compose loads it automatically). Every one has a sensible default baked into `docker-compose.yml` if you leave it unset.

| Variable | Used by | Purpose |
|---|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | postgres, backend | Local database credentials — also used to build the backend's internal `DATABASE_URL` |
| `APP_ENV` | backend | `development` enables the demo-data-seeding endpoints and the settlement-simulator job; anything else disables them |
| `DEBUG` | backend | Verbose SQL logging when `true` — leave `false` outside local debugging |
| `CORS_ORIGINS` | backend | JSON array of allowed browser origins — only matters if something calls the API directly from a browser, bypassing the Nginx proxy |
| `LLM_PROVIDER`, `GROQ_API_KEY`, `GROQ_MODEL`, `LLM_TEMPERATURE`, `LLM_TIMEOUT`, `MAX_RETRIES`, `RETRY_BACKOFF` | backend | Optional Groq-backed AI enrichment of retry decisions — the app runs deterministic-only if `GROQ_API_KEY` is blank |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET`, `RAZORPAY_BASE_URL`, `RAZORPAY_TIMEOUT` | backend | Optional real payment-gateway integration — the app runs in demo mode if these are blank |
| `SCHEDULER_TIMEZONE`, `SCHEDULER_RETRY_INTERVAL_SECONDS`, `SCHEDULER_SETTLEMENT_INTERVAL_SECONDS` | backend | Background job timing |
| `LOG_LEVEL` | backend | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |
| `VITE_API_URL` | frontend (build-time only) | Base API path baked into the built JS — leave as `/api/v1` for Docker so requests go through the Nginx proxy |

The full authoritative list (with defaults) lives in [`backend/app/config/settings.py`](backend/app/config/settings.py).

---

## Database schema on first boot

Only one Alembic migration exists in this repo
(`alembic/versions/8ace040fcca1_add_razorpay_integration.py`) — the base
schema predates it and was never captured as a migration. So on a genuinely
fresh database, `backend/init_db.py` (run automatically by
`backend/entrypoint.sh` before Uvicorn starts) creates the full schema
directly from the ORM models, then stamps Alembic's version table at
`head` — recording that baseline as applied without re-running it. On every
later restart it just runs a normal `alembic upgrade head`, so any migration
you add after this point applies normally.

If you add a new Alembic migration in the future, this behavior needs no
changes — it only affects the very first boot against an empty database.

---

## Troubleshooting

**`docker compose up` fails at the `postgres` healthcheck / backend keeps restarting**
Check `docker compose logs postgres` — usually a stale `postgres_data` volume
from a previous run with different credentials. Fix: `docker compose down -v`
then `docker compose up --build` to start with a clean volume.

**Frontend loads but every page shows a network/API error**
Check `docker compose logs backend` — if the backend container isn't
healthy, Nginx has nothing to proxy to. Also confirm you didn't override
`VITE_API_URL` to an absolute `http://localhost:8000/...` URL — for the
Docker workflow it should stay relative (`/api/v1`), which routes through
Nginx's internal proxy rather than requiring the browser to reach the
backend directly.

**Refreshing a page other than `/` gives a 404**
This means `frontend/nginx.conf` isn't the config actually running in the
container — rebuild the frontend image (`docker compose build frontend`).
The shipped config includes a `try_files ... /index.html` fallback
specifically so client-side routes survive a refresh.

**Changed backend code but nothing changed in the running container**
Docker images are a snapshot — rebuild after any source change:
`docker compose up --build`.

**Port already in use (3000 / 8000 / 5432)**
Something else on your machine is already bound to that port. Either stop
it, or change the left-hand side of the port mapping in `docker-compose.yml`
(e.g. `"3001:80"`) and use that port instead.

**Need a clean slate**
```bash
docker compose down -v      # stops everything, deletes the database volume
docker compose up --build   # rebuilds and starts fresh
```

**Want to run a one-off command inside a running container**
```bash
docker compose exec backend python -m backend.init_db   # re-run schema bootstrap manually
docker compose exec postgres psql -U $POSTGRES_USER -d $POSTGRES_DB
```

---

## Running without Docker

Each service can also run directly on your machine against a locally
installed Postgres:

```bash
# Backend
cp backend/.env.example backend/.env   # fill in DATABASE_URL etc.
pip install -r requirements.txt
alembic upgrade head                    # or: python -c "from backend.app.database.base import Base; from backend.app.database.database import engine; import backend.app.models; Base.metadata.create_all(engine)"
uvicorn backend.app.main:app --reload   # run from the repo root

# Frontend (separate terminal)
cd frontend
cp .env.example .env                    # VITE_API_URL should point at http://localhost:8000/api/v1
npm install
npm run dev
```

See `backend/.env.example` and `frontend/.env.example` for the full variable
list for this workflow — they're separate from the root `.env.example`,
which is specifically for Docker Compose (notably: `DATABASE_URL` differs,
since the backend container reaches Postgres via the hostname `postgres`,
not `localhost`).
