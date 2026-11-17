# Cover pages

Start each document with a full-bleed cover showing the page's title, its description and the version of the website, set very large, followed by a table of contents.

{{ previews("cover-pages") }}

=== "`mkdocs.yml`"

    {{ example("cover-pages/mkdocs.yml") }}

=== "`covers/front.html.j2`"

    {{ example("cover-pages/covers/front.html.j2") }}

=== "A page"

    ```markdown
    ---
    description: Text, lists, code, admonitions, tabs and footnotes, as they are printed.
    ---

    # Writing pages
    ```

- The front cover is a [Jinja template](../guide/cover-pages.md), rendered for each page: `page` is the page (`page.title`, `page.meta` for its front matter), and `extra` the `extra` settings of `mkdocs.yml`.
- `<style data-mkdocs-exporter-teleport="head">` moves the template's styles to the head of the document: its `@page :first` rule removes the margins of the first page and gives it a color.
- The template is rendered by Jinja: `extra.version.rsplit(".", 1)[0]` keeps the major and minor version (`2.4`), printed in large type. Its content stays in the flow of the page, so that it can't overflow onto another page.
- `toc` inserts a [table of contents](../guide/tables-of-contents.md#documents-of-pages) of the page's headings after the front cover, with their page numbers.

A page can use another cover, or none, in its front matter:

=== "Another cover"

    ```yaml
    ---
    exporter:
      pdf:
        covers:
          front: covers/release-notes.html.j2
    ---
    ```

=== "No cover"

    ```yaml
    ---
    exporter:
      pdf:
        covers:
          enabled: false
    ---
    ```

[:material-github: Browse the files of this example](https://github.com/adrienbrignon/mkdocs-exporter/tree/master/examples/cover-pages)
