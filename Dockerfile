FROM python:3.14-slim AS python_base
WORKDIR /app

FROM python_base AS builder
# heroku provides the SOURCE_VERSION env var with commit
ARG SOURCE_VERSION=0.0.0

ENV UV_NO_DEFAULT_GROUPS=1 \
    UV_LOCKED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_LOCKED=1 \
    UV_NO_MANAGED_PYTHON=1

COPY --from=ghcr.io/astral-sh/uv:0.11.31 /uv /uvx /bin/

COPY . /app

RUN uv sync

FROM python_base

COPY --from=builder /app /app

ENV PATH=$PATH:/app/.venv/bin

# default port, heroku can override this
ENV PORT=8080
CMD alembic upgrade head && \
    fastapi run --port $PORT --proxy-headers
