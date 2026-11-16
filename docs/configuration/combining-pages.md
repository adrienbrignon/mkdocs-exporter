# Combining pages

Books combine pages into single PDF documents. The pages of a book are assembled into a single HTML document, printed once by the browser:

```mermaid
flowchart LR
    pages[Pages] --> html[HTML document]
    html --> draft[Draft print]
    draft -- page numbers, blank pages, running heads --> final[Final print]
    final -- bookmarks --> pdf[PDF document]
```

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          books:
            - output: documentation.pdf
              covers: limits
              metadata:
                title: Documentation
                author: Jane Doe
```

Pages are combined in the order of the navigation, and numbered across the whole document: `{page}` and `{pages}` in [headers and footers](headers-and-footers.md), as well as `counter(page)` and `counter(pages)` in your own stylesheets, count the pages of the combined document.
The document's title, author and subject default to the website's (`site_name`, `site_author` and `site_description`).

Each page keeps its own `{page_title}` and `{section}`; the pages of the table of contents show its title.
What the browser can't print by itself (the page numbers of the table of contents, blank pages and `{section}`) is computed from a first print of the document's layout, then the document is printed again.

### In a single document

Since every page is part of the same HTML document:

- each page starts on a new page;
- identifiers are prefixed by page (e.g. `p2-installation`), so that footnotes, tabs and other references of different pages don't interfere: stylesheets and scripts targeting identifiers of the content (`#installation`) don't match them in combined documents;
- stylesheets and scripts loaded by some pages only are loaded once for the whole document, and the scripts of [`formats.pdf.scripts`](customizing-documents.md#scripts) run once;
- `@page :first` rules apply to the pages of front covers (in a page's own document, its first page is its front cover);
- styles teleported to the head by cover pages (`<style data-mkdocs-exporter-teleport="head">`) are included once when they are the same for every page; otherwise they only apply to their own page.

## Cover pages

The `covers` option tells which cover pages are kept:

| Value | Cover pages kept | For instance |
|---|---|---|
| `all` (*default*) | Every cover page | Pages printed one after another, each with its own covers |
| `none` | No cover page | Appendices, or documents opening with their table of contents |
| `limits` | The front cover of the first page and the back cover of the last page | A book, whose cover is the home page's |
| `book` | The front cover of every page and the back cover of the last page | Chapters opening with a title page |
| `front` | Every front cover page | Chapters opening with a title page, without a back cover |
| `back` | Every back cover page | Pages each ending with a summary page |

```yaml
books:
  - output: documentation.pdf
    covers: limits
```

A cover template can tell the home page apart, to give the combined document a cover of its own (see [The Field Guide](../examples/index.md#the-field-guide) example):

```html
<div class="title">{% raw %}{{ config.site_name if page.is_homepage else page.title }}{% endraw %}</div>
```

## Bookmarks and links

The combined document has bookmarks following the navigation: sections, pages and their headings (`h2`, `h3`).
Their depth can be changed, or set to `0` to disable them:

```yaml
books:
  - output: documentation.pdf
    outline: 2
```

Links between pages of the combined document point within the document, to the linked heading when there is one.
Other links point to the website (`site_url` or `formats.pdf.url`), or are relative to the combined document when the website has no URL.

Like the documents of pages, combined documents are tagged: their structure is described, so that screen readers can read them.
Tagging makes them about half as large again; it can be disabled:

```yaml
books:
  - output: documentation.pdf
    tagged: false
```

## Table of contents

A table of contents can be inserted after the first front cover:

```yaml
books:
  - output: documentation.pdf
    toc:
      enabled: true
      title: Contents
      depth: 2 # Pages and their second-level headings
```

Its appearance can be changed with CSS (`.mkdocs-exporter-toc` and the classes of the default [template](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs_exporter/core/resources/toc.html)), or replaced with a Jinja template of your own (`toc.template`, relative to `mkdocs.yml`).
Templates receive the `title` and the `entries` of the table of contents, each entry having a `title`, a `page` number, an `href` and `children`: navigation sections, then pages, then their headings.
For instance, a table of contents laid out as a table:

=== "`mkdocs.yml`"

    {{ example("toc-template/mkdocs.yml") }}

=== "`toc.html.j2`"

    {{ example("toc-template/toc.html.j2") }}

=== "`pdf.css`"

    {{ example("toc-template/pdf.css") }}

{{ previews("toc-template") }}

## Starting pages on the right

For printed books, pages can start on odd (right-hand) pages, blank pages (without headers nor footers) being inserted when needed:

```yaml
books:
  - output: documentation.pdf
    start: odd
```

## Several documents

`books` lists as many documents as needed. Patterns select the pages they contain, matched against the path of pages' source files (`*` matches any text, including `/`):

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          books:
            - output: pdf/user-guide.pdf
              include:
                - user-guide/*
            - output: pdf/reference.pdf
              include:
                - reference/*
              exclude:
                - reference/internal/*
```

Every option is available for each of them.

!!! example "Examples"

    - [A printed book](../examples/book.md): a cover, a table of contents, bookmarks and chapters starting on the right.
    - [One document per section](../examples/documents.md): several combined documents, selected with patterns.
