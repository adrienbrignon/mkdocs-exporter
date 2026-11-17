---
exporter:
  buttons:
    - title: I'm Feeling Lucky
      icon: material-star-outline
      attributes:
        class: md-content__button md-icon md-icon-spin
        href: https://www.youtube.com/watch?v=dQw4w9WgXcQ
        target: _blank
---

# Buttons

You can define custom buttons at the top of your pages.

!!! example "Try it out"

    A custom button is featured on this page, check it out!  
    You can find its configuration [below](#adding-buttons-to-a-specific-page).

With Material for MkDocs, buttons are icons next to the theme's own buttons (`icon` names a Material icon, `title` is its tooltip).
With the `readthedocs` theme and other themes, buttons are links showing their `title`, without icon.
A `class` attribute replaces the theme's classes.

## Adding a download button

The following configuration excerpt will add a download button to pages that have a PDF document:

```yaml
plugins:
  - exporter:
      buttons:
        - title: Download as PDF
          icon: material-file-download-outline
          enabled: !!python/name:mkdocs_exporter.formats.pdf.buttons.download.enabled
          attributes: !!python/name:mkdocs_exporter.formats.pdf.buttons.download.attributes
```

## Adding a button downloading a book

Pages that are part of a [book](books.md) can link to it.
The following button downloads the first book including the page, named after the book's title (`metadata.title`, the site's name by default):

```yaml
plugins:
  - exporter:
      buttons:
        - title: Download the documentation
          icon: material-book-arrow-down-outline
          enabled: !!python/name:mkdocs_exporter.formats.pdf.buttons.book.enabled
          attributes: !!python/name:mkdocs_exporter.formats.pdf.buttons.book.attributes
```

The books including a page are listed by `page.formats["pdf"]["books"]` (each with its `url`, relative to the website's root, and its `title`), for buttons of your own (see below).

## Defining a dynamic button

Like the download button above, any property of a button can be computed by a Python function, called with the page.
For instance, a button opening an issue about the page:

=== "`my_module/buttons.py`"

    ```python
    from urllib.parse import urlencode

    from mkdocs_exporter.page import Page


    def href(page: Page, **kwargs) -> str:
        """A link opening an issue about the page."""

        return "https://github.com/example/docs/issues/new?" + urlencode(
            {"title": f"Feedback on {page.title}"}
        )
    ```

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - exporter:
          buttons:
            - title: Report an issue
              icon: material-bug-outline
              attributes:
                href: !!python/name:my_module.buttons.href
                target: _blank
    ```

The module has to be importable when MkDocs reads its configuration: install it, or build your website with `PYTHONPATH=.` (e.g. `PYTHONPATH=. mkdocs build`, or `$env:PYTHONPATH = "."` first in PowerShell) when it sits next to `mkdocs.yml`.

## Adding buttons to a specific page

Pages can add buttons of their own with `exporter.buttons` in their [front matter](../reference/front-matter.md), besides those of the configuration.

Here's how it's configured for this page:

```yaml
---
{% set button = page.meta.exporter.buttons[0] -%}

exporter:
  buttons:
    - title: {{ button.title }}
      icon: {{ button.icon }}
      attributes:
        class: {{ button.attributes.class }}
        href: {{ button.attributes.href }}
        target: {{ button.attributes.target }}
---

# {{ page.title }}
```
