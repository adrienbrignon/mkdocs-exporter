# Front matter

Pages can change how their documents are generated in their front matter (or [metadata](https://www.mkdocs.org/user-guide/writing-your-docs/#meta-data)):

```yaml
---
pdf: true
author: Jane Doe
description: How to configure the plugin.
tags:
  - configuration
covers:
  front: covers/release-notes.html.j2
---

# Configuration
```

| Key | Effect | See |
|---|---|---|
| `pdf` | `false` leaves the page without a document; `true` gives it one in explicit mode (`formats.pdf.explicit`) | [Choosing pages](../configuration/generating-pdf-documents.md#choosing-pages) |
| `covers` | Templates replacing the cover pages of the page (`front`, `back`), relative to `mkdocs.yml` | [Per-page cover pages](../configuration/generating-pdf-documents.md#per-page-cover-pages) |
| `hide` | `covers` in the list leaves the page without cover pages | [Hiding cover pages](../configuration/generating-pdf-documents.md#hiding-cover-pages) |
| `toc` | `false` leaves out the table of contents of the page's document, `true` gives it one (instead of `formats.pdf.toc.enabled`) | [Table of contents](../configuration/generating-pdf-documents.md#table-of-contents) |
| `author` | The author of the document (`site_author` by default) | [Document information](../configuration/generating-pdf-documents.md#document-information) |
| `description` | The subject of the document (`site_description` by default) | [Document information](../configuration/generating-pdf-documents.md#document-information) |
| `keywords`, `tags` | The keywords of the document | [Document information](../configuration/generating-pdf-documents.md#document-information) |
| `buttons` | Buttons added to the page, besides those of `buttons` | [Adding buttons to a specific page](../configuration/adding-buttons-to-pages.md#adding-buttons-to-a-specific-page) |

Cover templates also receive every key of the front matter, as variables and in `page.meta` (e.g. `page.meta.description`).
