# Print styles

Number headings, print the address of links, mark every page as a draft, and keep content for the website or for documents only.

{{ previews("print-styles") }}

=== "`mkdocs.yml`"

    {{ example("print-styles/mkdocs.yml") }}

=== "`pdf.css`"

    {{ example("print-styles/pdf.css") }}

=== "A page"

    ```markdown
    <div class="mkdocs-exporter-ignore" markdown>

    !!! tip "Download"

        The documents are generated along with the website...

    </div>

    This document was printed from the Field Guide website.
    { data-decompose="true" }
    ```

- [Stylesheets](../configuration/customizing-documents.md#stylesheets) of the plugin only apply to documents: the website keeps its own styles.
- CSS counters number headings; `counter-reset` restarts the numbering of third-level headings at each second-level heading.
- `attr(href)` prints the address of links after them. Links to other pages point to the website (`site_url`), so their address is printed too: add `:not([href^="https://field-guide.example.com"])` to the selector to only print the address of other websites. In combined documents, links between pages point within the document, without an address.
- A `position: fixed` element of the body (a child or a pseudo-element of `body`, here `body::after`) is printed on every page, at the same place. Fixed elements inside the page's content are only printed on its first page.
- Elements of the `mkdocs-exporter-ignore` class are left out of documents, while elements with a `data-decompose="true"` attribute are left out of the website (here, using the `attr_list` extension).

[:material-github: Browse the files of this example](https://github.com/adrienbrignon/mkdocs-exporter/tree/master/examples/print-styles)
