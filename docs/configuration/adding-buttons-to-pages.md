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

As you saw in the previous example, Python functions can be used to dynamically resolve button attributes.  
Now, let's write a button that, when clicked, initiates a Google search using the current page's title as the query.

To begin with, let's write the function that will return the button's `href` attribute:

```python
from urllib.parse import urlencode
from mkdocs_exporter.page import Page

def href(page: Page, **kwargs) -> str:
  """The button's 'href' attribute."""

  return 'https://google.com/search?' + urlencode({'q': page.title})
```

Next, we can define the button and specify the path to the function previously defined (assuming it has been saved in the `button.py` file under the `my_module` module):

```yaml
plugins:
  - exporter:
      buttons:
        - title: Download as PDF
          icon: material-file-download-outline
          attributes:
            href: !!python/name:my_module.button.href
```

Repeat this process as needed; you can apply this method to any property of a button.

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
