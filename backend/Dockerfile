# --- LearnEas backend (Django + DRF + Channels/Daphne) ---
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dépendances système nécessaires à psycopg2 / Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        libjpeg62-turbo-dev \
        zlib1g-dev \
        curl \
        ffmpeg \
        gosu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN chmod +x /app/docker/entrypoint.sh \
    && groupadd --gid 10001 learneas \
    && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin learneas \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R learneas:learneas /app

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "--application-close-timeout", "10", "learneas.asgi:application"]
