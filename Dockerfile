
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

FROM base AS deps

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM deps AS final

WORKDIR /app

COPY Flask_routes.py .
COPY Model.py .
COPY Tables.py .

COPY index.html .

RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 5000

CMD ["sh", "-c", "gunicorn Flask_routes:app --bind 0.0.0.0:$PORT --worker-tmp-dir /tmp"]
