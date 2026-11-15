# Headers and footers

## Configuration

Headers and footers have a `left`, `center` and `right` part:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          header:
            left: "{site_name}"
            right: "{page_title}"
          footer:
            left: "{section}"
            right: "Page {page} of {pages}"
```

The following placeholders are available:

| Placeholder | Value |
|---|---|
| `{site_name}` | The name of the website (`site_name`) |
| `{page_title}` | The title of the page |
| `{section}` | The first or second-level heading the page starts with |
| `{page}` | The page number |
| `{pages}` | The number of pages |

In combined documents, pages are numbered across the whole document.

Headers and footers are not printed on cover pages; when they are configured, the back cover starts a new page.
They are printed in the margins of pages, so make sure your stylesheet leaves enough room (the default margins do).

## Using CSS

Headers and footers are generated as [page margin boxes](https://www.w3.org/TR/css-page-3/#margin-boxes): they can be styled, or written entirely, in your own [stylesheet](customizing-documents.md#stylesheets). For instance:

```css
@page {
  @top-center {
    font-family: Roboto, sans-serif;
    color: #7f7f7f;
  }

  @bottom-right {
    content: "Page " counter(page) " of " counter(pages);
  }
}

@page :first {
  @bottom-right {
    content: none;
  }
}
```

The generated rules come before your stylesheets, so they can be refined there.
Browsers don't support running headers in CSS (`string-set`): use the `{section}` and `{page_title}` placeholders, or [Paged.js](customizing-documents.md#using-paged-js).
