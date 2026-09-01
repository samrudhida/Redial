#!/bin/sh
# Docker container entrypoint for the backend service.
#
# 1. Prepare the database schema (waits for Postgres, creates/migrates the
#    schema — see init_db.py for why this isn't a plain `alembic upgrade`).
# 2. exec uvicorn so it becomes PID 1 — required for it to receive SIGTERM
#    directly from `docker stop` and shut down gracefully (the app's lifespan
#    handler stops the background scheduler cleanly on shutdown).
set -e

echo "Preparing database schema..."
python -m backend.init_db

echo "Starting Uvicorn..."
exec uvicorn backend.app.main:app --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
