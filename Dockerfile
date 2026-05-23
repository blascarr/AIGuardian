FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
COPY src ./src
COPY config ./config

RUN pip install --no-cache-dir -e ".[ml]"

COPY scripts ./scripts

EXPOSE 8080

CMD ["pihole-blocker"]
