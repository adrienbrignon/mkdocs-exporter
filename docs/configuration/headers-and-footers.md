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

Headers and footers are generated as [page margin boxes](https://www.w3.org/TR/css-page-3/#margin-boxes): for more control, write them in your own [stylesheet](customizing-documents.md#stylesheets) instead. For instance:

```css
h1 {
  string-set: chapter content(text);
}

@page {
  @top-right {
    content: string(chapter);
    font-size: 9pt;
    color: #7f7f7f;
  }

  @bottom-center {
    content: counter(page) " / " counter(pages);
  }
}

@page :first {
  @top-right {
    content: none;
  }
}
```

The generated rules come before your stylesheets, so they can be refined there too.
