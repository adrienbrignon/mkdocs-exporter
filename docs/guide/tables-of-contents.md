# Tables of contents

Documents can start with a table of contents, with page numbers: the document of each page lists its headings, and a [book](books.md) lists its pages and their headings.
The page numbers are filled from a first print of the document, which is then printed again.

## Documents of pages

The table of contents of the page's headings is inserted after the front cover:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          toc:
            enabled: true
            title: Contents # "Table of contents" by default
            depth: 3 # Second and third-level headings
```

Pages without headings besides their title don't get one, nor do books, which have a table of contents of their own.
A page can do without one, or have one while the option is disabled, in its [front matter](../reference/front-matter.md):

```yaml
---
exporter:
  pdf:
    toc:
      enabled: false
---
```

## Books

The table of contents of a book lists its pages, following the navigation, and their headings. It is inserted after the first front cover (`books` is under `formats.pdf`):

```yaml
books:
  - output: documentation.pdf
    toc:
      enabled: true
      title: Contents # "Table of contents" by default
      depth: 2 # Pages and their second-level headings
```

## Appearance

The appearance of tables of contents can be changed with CSS (`.mkdocs-exporter-toc` and the classes of the default [template](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs_exporter/core/resources/toc.html)), or replaced with a Jinja template of your own (`toc.template` of the documents of pages or of a book, relative to `mkdocs.yml`).
Templates receive the `title` and the `entries` of the table of contents, each entry having a `title`, a `page` number, an `href` and `children`: navigation sections, then pages, then their headings.
For instance, a table of contents laid out as a table:

=== "`mkdocs.yml`"

    {{ example("toc-template/mkdocs.yml") }}

=== "`toc.html.j2`"

    {{ example("toc-template/toc.html.j2") }}

=== "`pdf.css`"

    {{ example("toc-template/pdf.css") }}

{{ previews("toc-template") }}
