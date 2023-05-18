---
buttons:
  - title: I'm Feeling Lucky
    href: https://www.youtube.com/watch?v=dQw4w9WgXcQ
    icon: material-star-outline
    target: _blank
---

# Setting up buttons

You can define custom buttons at the top of your pages.

## Configuration

As this feature is provided by the `mkdocs/exporter/extras` plugin, you'll need to add it to your list of plugins:

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
          href: !!python/name:mkdocs_exporter.plugins.pdf.button.href
          download: !!python/name:mkdocs_exporter.plugins.pdf.button.download
```

The functions referenced in this configuration are provided by the **MkDocs Exporter** plugin.

### Defining a dynamic button

As you've seen in the previous example, you can use Python functions to resolve the attributes of a button dynamically.
Let's write a button that when clicked, it starts a search on Google with the current page's title as query.

First of all, let's write the function that will resolve to the `href` attribute's of the button:

```python
from urllib.parse import urlencode
from mkdocs_exporter.page import Page

def href(page: Page) -> str:
  """The button's 'href' attribute."""

  return 'https://google.com/search' + urlencode({q: page.title})
```

Then, we can define a button and specify the previously defined function (assuming it has been saved to `my_module/button.py`):

```yaml
plugins:
  - mkdocs/exporter/extras:
      buttons:
        - title: Search on Google
          icon: material-google
          href: !!python/name:my_module.button.href
```

Rinse and repeat, you can use this method for any property of a button.

### Adding a button on a page

You can also use `meta` tags to define buttons on a per-page basis.  
Here's the configuration used by this page:

```yaml
---
{% set button = page.meta.buttons[0] -%}

buttons:
  - title: {{ button.title }}
    href: {{ button.href }}
    icon: {{ button.icon }}
    target: {{ button.target }}
---

# {{ page.title }}

[...]
```
