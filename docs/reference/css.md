# CSS classes and attributes

## Classes for your content

| Class | Effect |
|---|---|
| `page-break` / `page-break-after` | Starts a new page after the element |
| `page-break-before` | Starts a new page before the element |
| `avoid-page-break` | Keeps the element on a single page when possible |
| `mkdocs-exporter-ignore` | Removes the element from PDF documents |
| `mkdocs-exporter-only` | Removes the element from the website (it is only in PDF documents) |

See [Utility classes](../guide/styles-and-scripts.md#utility-classes).

## Attributes

| Attribute | Effect |
|---|---|
| `data-mkdocs-exporter-teleport="<selector>"` | Moves the element into the element the CSS selector matches, in documents and in the website's pages (see [Moving elements](../guide/styles-and-scripts.md#moving-elements)) |
| `data-teleport="<selector>"` | Deprecated, replaced by `data-mkdocs-exporter-teleport` |
| `data-decompose="true"` | Deprecated, replaced by the `mkdocs-exporter-only` class |

## Classes of documents

The exporter gives these classes to the elements it adds to documents, to style them:

| Class | Element |
|---|---|
| `mkdocs-exporter-front-cover`, `mkdocs-exporter-back-cover` | The [cover pages](../guide/cover-pages.md), wrapping the content of their template |
| `mkdocs-exporter-title` | The page's title, inserted when its content has no first-level heading ([`title`](../guide/documents.md#page-titles)) |
| `mkdocs-exporter-toc` | A [table of contents](../guide/tables-of-contents.md), wrapping its template: `mkdocs-exporter-toc-title`, `mkdocs-exporter-toc-entries` (lists), `mkdocs-exporter-toc-entry` and `mkdocs-exporter-toc-level-N` (entries), `mkdocs-exporter-toc-label` and `mkdocs-exporter-toc-page` (their title and page number) |
| `mkdocs-exporter-part` | In [books](../guide/books.md), each page of the website (identified by `mkdocs-exporter-part-N`, from `0`) |
| `mkdocs-exporter-blank` | In books, the blank pages inserted by `start: odd` |

## Named pages

The exporter prints some elements on [named pages](https://developer.mozilla.org/en-US/docs/Web/CSS/page), which `@page` rules can style:

| Page | Pages |
|---|---|
| `mkdocs-exporter-cover` | Back covers, when headers or footers are configured |
| `mkdocs-exporter-front-cover` | In books, front covers (`@page :first` rules of your stylesheets and covers apply to them) |
| `mkdocs-exporter-toc` | In books, the table of contents |
| `mkdocs-exporter-blank` | In books, blank pages |

In the document of a page, its front cover is its first page (`@page :first`).
