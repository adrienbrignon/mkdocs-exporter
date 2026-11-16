# Continuous integration

Building documents requires a browser: install it with Playwright, along with its system dependencies, before building your documentation.

These recipes build the website with [ProperDocs](https://github.com/ProperDocs/properdocs), the continuation of MkDocs 1.x, which reads `properdocs.yml` (or `mkdocs.yml`, preferably passed with `-f mkdocs.yml`). With MkDocs, leave `properdocs` out and run `mkdocs build` instead.

## GitHub Actions

Building the website and publishing it on GitHub Pages:

{% raw %}
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
      - uses: astral-sh/setup-uv@v10.3.3
      - name: Install dependencies
        run: uv venv && uv pip install properdocs mkdocs-material "mkdocs-exporter>=7.0.0rc1"
      - name: Get Playwright's version
        id: playwright
        run: echo "version=$(.venv/bin/python -c 'import importlib.metadata as m; print(m.version("playwright"))')" >> "$GITHUB_OUTPUT"
      - name: Cache the browser
        uses: actions/cache@v6
        with:
          path: ~/.cache/ms-playwright
          key: playwright-${{ runner.os }}-${{ steps.playwright.outputs.version }}
      - name: Cache documents
        uses: actions/cache@v6
        with:
          path: .cache/plugin/exporter
          key: mkdocs-exporter-${{ github.run_id }}
          restore-keys: mkdocs-exporter-
      - name: Install the browser
        run: .venv/bin/playwright install --with-deps --only-shell chromium
      - name: Build the documentation
        run: .venv/bin/properdocs build -f mkdocs.yml
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - id: deployment
        uses: actions/deploy-pages@v5
```
{% endraw %}

- The browser is cached for each version of Playwright (in `~/Library/Caches/ms-playwright` on macOS, `~\AppData\Local\ms-playwright` on Windows); `--with-deps` still installs its system libraries on every run.
- Documents are cached too: only the pages that changed since the last run are rendered (see [Cache](../configuration/generating-pdf-documents.md#cache)).
- GitHub Pages has to be published by GitHub Actions (*Settings* › *Pages* › *Source*).

## GitLab CI

The official Playwright image ships the browser and its dependencies: install the version of Playwright matching the image's tag.

```yaml
pages:
  image: mcr.microsoft.com/playwright/python:v1.65.2-noble
  script:
    - pip install properdocs mkdocs-material "mkdocs-exporter>=7.0.0rc1" playwright==1.65.2
    - properdocs build -f mkdocs.yml --site-dir public
  artifacts:
    paths:
      - public
```

If your website is published under a sub-path (e.g. `https://group.gitlab.io/project/`), set `site_url` accordingly: links and download buttons are resolved from it.

## Docker

```dockerfile
FROM mcr.microsoft.com/playwright/python:v1.65.2-noble

WORKDIR /docs
RUN pip install properdocs mkdocs-material "mkdocs-exporter>=7.0.0rc1" playwright==1.65.2
COPY . .
RUN properdocs build -f mkdocs.yml
```

Or, starting from a smaller image (Playwright's driver needs `libatomic1` to install the browser):

```dockerfile
FROM python:3.13-slim

WORKDIR /docs
RUN apt-get update \
 && apt-get install -y --no-install-recommends libatomic1 \
 && rm -rf /var/lib/apt/lists/*
RUN pip install properdocs mkdocs-material "mkdocs-exporter>=7.0.0rc1" \
 && playwright install --with-deps --only-shell chromium
COPY . .
RUN properdocs build -f mkdocs.yml
```

This project's own [Dockerfile](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/Dockerfile) builds this documentation with [uv](https://docs.astral.sh/uv/).

When running Chromium in containers, you might need to give it more shared memory (`docker run --ipc=host` or `--shm-size=1g`).
