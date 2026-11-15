# Writing pages

Pages are written in Markdown, like the rest of the website: everything Markdown extensions render can be printed.

## Text and lists

Paragraphs flow from one page to the next, and lists keep their numbering:

1. Write the page in Markdown.
2. Build the website with `mkdocs build`.
3. Download the PDF document of the page.

Text can be **bold**, *italic*, `code`, or a [link to another page](printing.md), which points to that page in the combined document.

### Footnotes

Footnotes are listed at the end of the page.[^1]

[^1]: Footnotes of different pages don't mix in the combined document.

## Code

Code blocks are highlighted, and continue on the next page when they are long:

```python
from pathlib import Path


def documents(site: Path) -> list[Path]:
    """The PDF documents of a built website."""

    return sorted(site.rglob("*.pdf"))


for document in documents(Path("site")):
    print(document)
```

## Admonitions

!!! note

    Admonitions are printed like on the website.

??? info "Collapsed blocks"

    Collapsed blocks are opened in documents, so that nothing is missing.

## Tabs

Every tab is printed, with its label:

=== "Material"

    The `material` theme has dedicated support.

=== "Read the Docs"

    The `readthedocs` theme has dedicated support too.

=== "Other themes"

    Other themes are supported on a best-effort basis.
