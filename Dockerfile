FROM ghcr.io/astral-sh/uv:python3.13-alpine AS builder

COPY --chown=1000:1000 . /app
WORKDIR /app

USER 1000

ENV UV_CACHE_DIR=/app/uv_cache
RUN uv sync --locked --compile-bytecode

CMD ["uv", "run", "main.py"]
