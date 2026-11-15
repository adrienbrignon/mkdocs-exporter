# One document per section

Generate several combined documents: the whole guide without its home page, and a document for each section of the navigation.

{{ previews("documents") }}

=== "`mkdocs.yml`"

    {{ example("documents/mkdocs.yml") }}

=== "Output"

    ```
    site/
    ├── pdf/
    │   ├── field-guide.pdf   # Every page but the home page
    │   ├── guide.pdf         # guide/writing.md and guide/printing.md
    │   └── reference.pdf     # reference/paper-sizes.md and reference/glossary.md
    ├── guide/
    │   ├── writing/
    │   │   ├── index.html
    │   │   └── index.pdf
    │   └── ...
    └── ...
    ```

- [`aggregators`](../configuration/combining-pages.md#several-documents) lists combined documents, each with the options of `aggregator` (covers, table of contents, bookmarks...).
- `include` and `exclude` select pages by the path of their source file, relative to the `docs` directory: `*` matches any text, including `/`. Pages are in the order of the navigation.
- Each document is numbered on its own: `{pages}` counts the pages of the document.
- `metadata` sets the information shown by PDF readers, the title being the website's name by default.

[:material-github: Browse the files of this example](https://github.com/adrienbrignon/mkdocs-exporter/tree/master/examples/documents)
