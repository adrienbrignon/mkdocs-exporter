# Page numbers

Number pages, and repeat the website's name and the current section at the top of each page.

{{ previews("page-numbers") }}

=== "`mkdocs.yml`"

    {{ example("page-numbers/mkdocs.yml") }}

=== "`pdf.css`"

    {{ example("page-numbers/pdf.css") }}

- `header` and `footer` place text in the margins of every page, at the `left`, `center` or `right`. Their [placeholders](../guide/headers-and-footers.md) are replaced by the website's name (`{site_name}`), the heading the page starts with (`{section}`), the page number (`{page}`) and the number of pages (`{pages}`).
- The stylesheet sets the size of pages and their margins, leaving room for the header and the footer.
- Headers and footers are [page margin boxes](https://www.w3.org/TR/css-page-3/#margin-boxes): the stylesheet styles them with `@top-left` and `@top-right` rules, which win over the plugin's own (each box needs a rule of its own).

To number pages without anything else, a footer is enough:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          footer:
            center: "{page} / {pages}"
```

[:material-github: Browse the files of this example](https://github.com/adrienbrignon/mkdocs-exporter/tree/master/examples/page-numbers)
