FROM docker.io/ubuntu:22.04 as base
WORKDIR /usr/src/app

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      g++ \
      gcc \
      git \
      python3 \
      python3-venv \
      gnupg2 \
      libffi-dev \
      make \
      wget \
 && rm -rf /var/lib/apt/lists/*


FROM base as builder

ENV POETRY_VERSION=1.8.3 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python3 -m venv .venv

COPY mkdocs_exporter/ mkdocs_exporter/
COPY pyproject.toml poetry.lock Makefile README.md ./

RUN . .venv/bin/activate \
 && pip install poetry \
 && make install \
 && playwright install chrome

COPY . .

RUN . .venv/bin/activate \
 && make build


FROM docker.io/nginx:1.27.0

COPY --from=builder /usr/src/app/dist /usr/share/nginx/html
