ifeq ($(origin .RECIPEPREFIX), undefined)
  $(error This Make does not support .RECIPEPREFIX. Please use GNU Make 4.0 or later)
endif

PDF = false
DEBUG = false

.RECIPEPREFIX = >
.PHONY: install build serve clean fclean re browser

all: build

install:
> poetry install $(ARGS)
> playwright install

browser:
> poetry run playwright install chrome $(if $(FORCE),--force,)

build:
>@ poetry run mkdocs build

serve:
>@ poetry run mkdocs serve

clean:
> $(RM) -rf dist/

fclean: clean
> $(RM) -rf .venv/

re: clean all
