ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif

PDF = true
DEBUG = false

.RECIPEPREFIX = >
.PHONY: install build serve clean fclean re browser

all: build

install:
> poetry install $(ARGS)

browser:
> poetry run playwright install $(if $(FORCE),--force,) --with-deps

build:
>@ MKDOCS_EXPORTER_PDF=$(PDF) poetry run mkdocs build

serve:
>@ MKDOCS_EXPORTER_PDF=$(PDF) poetry run mkdocs serve

clean:
> $(RM) -rf dist/

fclean: clean
> $(RM) -rf .venv/

re: clean all
