FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

COPY api api
COPY config config
COPY pipeline pipeline
COPY output/snapshot_explorer_catalog.json output/snapshot_explorer_catalog.json

RUN mkdir -p /app/data/analytics_portal /app/output

ENV PYTHONUNBUFFERED=1
ENV PORTAL_AUTH_DATABASE_URL=sqlite:////app/data/analytics_portal/portal_auth.db

CMD ["sh", "-c", "uvicorn api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
