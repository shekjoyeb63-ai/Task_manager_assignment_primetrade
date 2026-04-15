# ── Stage 1: base ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

# Set environment defaults
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies (needed for some Python packages)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# ── Stage 2: dependencies ───────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# ── Stage 3: final image ────────────────────────────────────────────────────────
FROM deps AS final

WORKDIR /app

# Copy application source
COPY Flask_routes.py .
COPY Model.py .
COPY Tables.py .

# Optional: copy frontend (static file, served separately or for reference)
COPY index.html .

# Non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

EXPOSE 5000

# Use Gunicorn in production; Flask dev server for local/testing
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "60", "Flask_routes:app"]
