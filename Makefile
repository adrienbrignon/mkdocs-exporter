ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif

PDF ?= true
PDF_AGGREGATOR ?= true

.RECIPEPREFIX = >
.PHONY: all install browser lint format typecheck test build serve examples dist clean fclean re

all: lint typecheck test

install:
> uv sync $(ARGS)

browser:
> uv run playwright install --only-shell chromium $(if $(WITH_DEPS),--with-deps,) $(if $(FORCE),--force,)

lint:
> uv run ruff check
> uv run ruff format --check

format:
> uv run ruff check --fix
> uv run ruff format

typecheck:
> uv run mypy

test:
> uv run pytest $(ARGS)

build:
>@ MKDOCS_EXPORTER_PDF=$(PDF) MKDOCS_EXPORTER_PDF_AGGREGATOR=$(PDF_AGGREGATOR) uv run mkdocs build $(ARGS)

serve:
>@ MKDOCS_EXPORTER_PDF=$(PDF) MKDOCS_EXPORTER_PDF_AGGREGATOR=$(PDF_AGGREGATOR) uv run mkdocs serve $(ARGS)

examples:
> @for theme in material readthedocs; do \
>   uv run mkdocs build -q -f examples/project/mkdocs.yml -t $$theme -d $(CURDIR)/.cache/examples/$$theme || exit 1; \
>   cp .cache/examples/$$theme/guide/writing/index.pdf examples/themes/$$theme.pdf; \
> done
> cp .cache/examples/material/example.pdf examples/example.pdf

dist:
> uv build

clean:
> $(RM) -r dist/ site/ .pytest_cache/ .mypy_cache/ .ruff_cache/

fclean: clean
> $(RM) -r .venv/

re: clean all
