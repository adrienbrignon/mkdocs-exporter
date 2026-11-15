ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif

PDF ?= true
BOOKS ?= true

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
>@ MKDOCS_EXPORTER_PDF=$(PDF) MKDOCS_EXPORTER_BOOKS=$(BOOKS) uv run mkdocs build $(ARGS)

serve:
>@ MKDOCS_EXPORTER_PDF=$(PDF) MKDOCS_EXPORTER_BOOKS=$(BOOKS) uv run mkdocs serve $(ARGS)

examples:
> uv run python examples/build.py

dist:
> uv build

clean:
> $(RM) -r dist/ site/ .pytest_cache/ .mypy_cache/ .ruff_cache/

fclean: clean
> $(RM) -r .venv/

re: clean all
