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

Documents are laid out by Chromium, which supports page sizes (they can differ from a page to another), margins, [margin boxes](https://www.w3.org/TR/css-page-3/#margin-boxes) with page counters, named pages (`page: ...`), `@page :first` and page breaks. Running headers are available through [headers and footers](headers-and-footers.md); for other features of the [CSS Generated Content for Paged Media](https://www.w3.org/TR/css-gcpm-3/) module, see [Using Paged.js](#using-paged-js).

## Page titles

Some themes don't print the page's title when its content has no first-level heading. The `title` option inserts it in documents:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          title: true
```

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
   * Once the page and the website's scripts are loaded.
   */
  before: async () => {},

  /**
   * Then, e.g. to wait for diagrams to be drawn.
   */
  render: async () => {
    if (window.mermaid) {
      await mermaid.run({ querySelector: '.mermaid' });
    }
  },

  /**
   * Last, right before printing.
   */
  after: async () => {},
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

## Using Paged.js

[Paged.js](https://pagedjs.org/) implements features of [CSS Generated Content for Paged Media](https://www.w3.org/TR/css-gcpm-3/) that browsers lack, such as running headers (`string-set`), page references (`target-counter`) or footnotes.
To use it, download [`paged.polyfill.min.js`](https://unpkg.com/pagedjs@0.4.3/dist/paged.polyfill.min.js) to your project and load it after a script running it before documents are printed:

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - exporter:
          formats:
            pdf:
              scripts:
                - resources/scripts/pagedjs.js
                - resources/scripts/paged.polyfill.min.js
    ```

=== "`resources/scripts/pagedjs.js`"

    ```javascript
    window.PagedConfig = { auto: false };
    window.MkDocsExporter = {
      render: () => window.PagedPolyfill.preview(),
    };
    ```

Paged.js lays out pages in JavaScript: expect documents to take longer to generate, especially combined ones.
Paged.js 0.4 also fails on some `:nth-child(An+B)` selectors, such as those of the `readthedocs` theme.

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
