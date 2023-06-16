---
buttons:
  - title: I'm Feeling Lucky
    icon: material-star-outline
    attributes:
      class: md-content__button md-icon md-icon-spin
      href: https://www.youtube.com/watch?v=dQw4w9WgXcQ
      target: _blank
---

# Setting up buttons

You can define custom buttons at the top of your pages.

!!! example "Try it out"

    A custom button is featured on this page, check it out!

## Configuration

This feature is provided by the `mkdocs/exporter/extras` plugin, you'll need to add it to your list of plugins:

```yaml
plugins:
  - mkdocs/exporter
  - mkdocs/exporter/extras
```

## Usage

### Adding a download button

This example will add a download button at the top of all pages that have a corresponding PDF document:

```yaml
plugins:
  - mkdocs/exporter/extras:
      buttons:
        - title: Download as PDF
          icon: material-file-download-outline
          enabled: !!python/name:mkdocs_exporter.plugins.pdf.button.enabled
          attributes:
            href: !!python/name:mkdocs_exporter.plugins.pdf.button.href
            download: !!python/name:mkdocs_exporter.plugins.pdf.button.download
```

The functions referenced in this configuration are provided by the **MkDocs Exporter** plugin.

!!! info

    Currently, icons are only available when using the [`material`](https://github.com/squidfunk/mkdocs-material) theme.

### Defining a dynamic button

As you've seen in the previous example, you can use Python functions to resolve button's attributes dynamically.  
Let's write a button that when clicked, it starts a search on Google with the current page's title as query.

First of all, let's write the function that will return the button's `href` attribute:

```python
from urllib.parse import urlencode
from mkdocs_exporter.page import Page

def href(page: Page, **kwargs) -> str:
  """The button's 'href' attribute."""

  return 'https://google.com/search' + urlencode({q: page.title})
```

Then, we can define the button and specify the path to the previously defined function (assuming it has been saved under the `my_module` module, in `button.py`):

```yaml
plugins:
  - mkdocs/exporter/extras:
      buttons:
        - title: Search on Google
          icon: material-google
          attributes:
            href: !!python/name:my_module.button.href
```

Rinse and repeat, you can use this method for any property of a button.

### Adding button on a specific page

You can also use the `buttons` meta tag to define buttons on a per-page basis.  
Here's the configuration currently used by this page:

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

[...]
```
