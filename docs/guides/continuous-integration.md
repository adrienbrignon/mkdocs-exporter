# Continuous integration

Building documents requires a browser: install it with Playwright, along with its system dependencies, before building your documentation.

## GitHub Actions

```yaml
name: Documentation

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v6
        with:
          python-version: '3.13'
      - name: Install dependencies
        run: pip install mkdocs-material mkdocs-exporter
      - name: Install the browser
        run: playwright install --with-deps --only-shell chromium
      - name: Build the documentation
        run: mkdocs build
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site
```

!!! tip
    Cache `~/.cache/ms-playwright` (keyed by Playwright's version) to avoid downloading the browser on every run, the system dependencies still need to be installed with `playwright install-deps chromium`.

## GitLab CI

The official Playwright image ships the browser and its dependencies. Use the tag matching the version of Playwright installed by your project (`pip show playwright`):

```yaml
pages:
  image: mcr.microsoft.com/playwright/python:v1.65.2-noble
  script:
    - pip install mkdocs-material mkdocs-exporter
    - mkdocs build --site-dir public
  artifacts:
    paths:
      - public
```

If your website is published under a sub-path (e.g. `https://group.gitlab.io/project/`), set `site_url` accordingly: links and download buttons are resolved from it.

## Docker

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.65.2-noble

WORKDIR /docs
RUN pip install mkdocs-material mkdocs-exporter
COPY . .
RUN mkdocs build
```

Or, starting from a smaller image:

```dockerfile
FROM python:3.13-slim

WORKDIR /docs
RUN pip install mkdocs-material mkdocs-exporter \
 && playwright install --with-deps --only-shell chromium
COPY . .
RUN mkdocs build
```

This project's own [Dockerfile](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/Dockerfile) builds this documentation with [uv](https://docs.astral.sh/uv/).

When running Chromium in containers, you might need to give it more shared memory (`docker run --ipc=host` or `--shm-size=1g`).
