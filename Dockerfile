# syntax=docker/dockerfile:1

FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder
WORKDIR /usr/src/app

ENV DISABLE_MKDOCS_2_WARNING=true \
    NO_MKDOCS_2_WARNING=1 \
    PATH="/usr/src/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update \
 && apt-get install -y --no-install-recommends git libatomic1 libcairo2 \
 && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY mkdocs_exporter/ mkdocs_exporter/

RUN uv sync --locked --no-default-groups --group docs \
 && playwright install --with-deps --only-shell chromium

COPY . .

RUN mkdocs build


FROM docker.io/nginx:stable-alpine

COPY --from=builder /usr/src/app/site /usr/share/nginx/html
