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

COPY --from=ghcr.io/astral-sh/uv:0.13.5 /uv /uvx /bin/

COPY pyproject.toml uv.lock *.md LICENSE config.toml ./
RUN uv sync --no-install-project

COPY valhalla valhalla
COPY migrations migrations

RUN uv sync

FROM node:26 AS frontend
# Install pnpm from ghcr
COPY --from=ghcr.io/pnpm/pnpm:12 /opt/pnpm /opt/pnpm
RUN for bin in pnpm pn pnpx pnx; do ln -s "/opt/pnpm/$bin" "/usr/local/bin/$bin"; done

WORKDIR /app/frontend

# Install packages
COPY frontend/package.json frontend/pnpm-lock.yaml ./
RUN pnpm install

# Copy files over
COPY frontend/ ./

# Build the app
RUN pnpm build

FROM python_base

COPY --from=builder /app /app
COPY --from=frontend /app/frontend/dist /app/frontend/dist

ENV PATH=$PATH:/app/.venv/bin \
    LITESTAR_APP=valhalla.app:create_app

# default port, heroku can override this
ENV PORT=8080
CMD litestar db upgrade --no-prompt && \
    litestar run \
    --host 0.0.0.0 \
    --port $PORT
