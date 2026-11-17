# Cover pages

Cover pages are added at the beginning (`front`) and at the end (`back`) of documents. They are [Jinja](https://jinja.palletsprojects.com/) templates rendering HTML, with styles of their own:

{{ previews("field-guide:5", "field-guide:6") }}

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - exporter:
          formats:
            pdf:
              covers:
                front: covers/front.html.j2
                back: covers/back.html.j2
    ```

=== "`covers/front.html.j2`"

    {{ example("field-guide/covers/front.html.j2") }}

=== "`covers/back.html.j2`"

    {{ example("field-guide/covers/back.html.j2") }}

These covers are those of the [Field Guide](../examples/index.md#the-field-guide) example, and the [Cover pages](../examples/cover-pages.md) example shows another one.

Templates have access to:

| Variable | Value | For instance |
|---|---|---|
| `page` | The page | {% raw %}`{{ page.title }}`, `{{ page.url }}`, `{{ page.parent.title }}` (its section), `{{ page.is_homepage }}`, `page.toc` (its headings){% endraw %} |
| `page.meta` | The page's metadata (front matter) | {% raw %}`{{ page.meta.description }}`{% endraw %} |
| `config` | The MkDocs configuration | {% raw %}`{{ config.site_name }}`, `{{ config.site_author }}`{% endraw %} |
| `extra` | The `extra` section of the configuration | {% raw %}`{{ extra.version }}`{% endraw %} |

The page's metadata are also available as variables (e.g. {% raw %}`{{ description }}`{% endraw %}).
When the [macros](https://github.com/fralau/mkdocs_macros_plugin) plugin is enabled, templates are rendered with its environment: its variables (such as `navigation`, every page of the website), macros and filters are available too.

- Covers are inserted in the flow of the document, wrapped in `.mkdocs-exporter-front-cover` and `.mkdocs-exporter-back-cover`: end the front cover with a page break (`break-after: page` on its outer element, as in the examples), and start the back cover with one (`break-before: page`), unless headers or footers are configured (the back cover is then on a page of its own).
- `<style data-mkdocs-exporter-teleport="head">` moves styles to the document's head, where they take precedence over your stylesheets: `@page :first` rules style the front cover's page (e.g. without margins, with a background).
- Paths starting with `/` (like `/assets/images/logo.png`) are resolved from the root of the website.
- Headers and footers aren't printed on cover pages. A cover can use a named page of its own (e.g. `page: colophon`, styled with `@page colophon`): headers and footers are printed there unless you empty its margin boxes (`content: none`), as the Field Guide's back cover does.
- Decorations drawn in the background of the cover's page stay in place, whatever the space the theme leaves above the content: prefer them to elements as tall as the page, which may overflow onto a blank page.

## Per-page cover pages

Pages can override cover pages in their front matter (paths are relative to `mkdocs.yml`):

```yaml
---
exporter:
  pdf:
    covers:
      front: resources/templates/covers/special.html.j2
---
```

## Hiding cover pages

Pages can also opt out of cover pages:

```yaml
---
exporter:
  pdf:
    covers:
      enabled: false
---
```
