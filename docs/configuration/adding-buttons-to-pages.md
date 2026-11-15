---
buttons:
  - title: I'm Feeling Lucky
    icon: material-star-outline
    attributes:
      class: md-content__button md-icon md-icon-spin
      href: https://www.youtube.com/watch?v=dQw4w9WgXcQ
      target: _blank
---

# Adding buttons to pages

You can define custom buttons at the top of your pages.

!!! example "Try it out"

    A custom button is featured on this page, check it out!  
    You can find its configuration [below](#adding-buttons-to-a-specific-page).

## Usage

### Adding a download button

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

### Defining a dynamic button

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

The module has to be importable when MkDocs reads its configuration: install it, or build your website with `PYTHONPATH=.` (e.g. `PYTHONPATH=. mkdocs build`) when it sits next to `mkdocs.yml`.

### Adding buttons to a specific page

You can add buttons to pages using the buttons field in your page's front matter, enabling you to define buttons specific to each page.

Here's how it's configured for this page:

```yaml
---
{% set button = page.meta.buttons[0] -%}

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
