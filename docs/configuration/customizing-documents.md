# Customizing documents

## Stylesheets

Documents are styled like your website, with print media rules. Custom stylesheets apply to PDF documents only, which is the place for [CSS Paged Media](https://www.w3.org/TR/css-page-3/) rules (page size, margins, margin boxes...):

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - exporter:
          formats:
            pdf:
              stylesheets:
                - resources/stylesheets/pdf.css
    ```

=== "`resources/stylesheets/pdf.css`"

    ```css
    @page {
      size: A4;
      margin: 1.20cm;

      @bottom-center {
        content: "Page " counter(page) " of " counter(pages);
      }
    }

    .front-cover {
      page-break-after: always;

      .title {
        font-size: 26pt;
      }
    }
    ```

Stylesheets are plain CSS: nesting is supported, Sass isn't (see the [migration guide](../migration/v7.md#sass)).

[Paged.js](https://pagedjs.org/documentation/) implements the paged media features Chromium lacks, such as running headers (`string-set`) or page references (`target-counter`).

## Utility classes

These classes are available in PDF documents:

| Class | Effect |
|---|---|
| `page-break` / `page-break-after` | Starts a new page after the element |
| `page-break-before` | Starts a new page before the element |
| `avoid-page-break` | Keeps the element on a single page when possible |
| `mkdocs-exporter-ignore` | Removes the element from PDF documents |

For instance, with the `attr_list` and `md_in_html` extensions:

```markdown
<div class="page-break"></div>

This paragraph won't be printed.
{ .mkdocs-exporter-ignore }
```

Conversely, elements having a `data-decompose="true"` attribute are removed from the website but kept in PDF documents.

## Scripts

Custom scripts are executed in PDF documents only:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          scripts:
            - resources/scripts/pdf.js
```

Scripts can define hooks, awaited by the exporter:

```javascript
window.MkDocsExporter = {
  /**
   * Before rendering, once the website's scripts have run.
   * Paged.js is available as `window.Paged`, e.g. to register handlers.
   */
  before: async () => {},

  /**
   * Before rendering, e.g. to wait for diagrams to be drawn.
   */
  render: async () => {
    if (window.mermaid) {
      await mermaid.run({ querySelector: '.mermaid' });
    }
  },

  /**
   * Once pages have been rendered.
   */
  after: async (flow) => {},
};
```

Fonts, images, MathJax and Material for MkDocs' diagrams are awaited automatically. When other scripts need more time, either use a hook or give them a delay (in milliseconds):

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          browser:
            delay: 500
```

## Browser

The browser can be configured too:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          browser:
            timeout: 60000 # Time given to each document to render (ms)
            channel: chrome # Use an installed browser instead of Chromium
            debug: true # Log the browser's console
            args: [] # Extra command-line arguments
```
