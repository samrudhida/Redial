# Backend Dockerfile — FastAPI (Uvicorn) service.
#
# Build context is the REPO ROOT (not backend/), because this needs
# requirements.txt, alembic.ini, and alembic/ from the root alongside the
# backend/ package itself — see docker-compose.yml's `build.context: .`.
#
# Single stage: psycopg2-binary ships prebuilt wheels with libpq bundled in,
# and every other dependency is pure Python, so no compiler/system packages
# are needed to build or run this image.
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies before copying application code — this layer is only
# rebuilt when requirements.txt actually changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Application code, plus the Alembic config/migrations it needs at startup.
COPY backend/ ./backend/
COPY alembic.ini ./alembic.ini
COPY alembic/ ./alembic/

RUN chmod +x backend/entrypoint.sh \
    && useradd --no-create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["backend/entrypoint.sh"]
