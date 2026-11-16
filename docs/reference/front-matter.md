# Front matter

Pages change how their documents are generated with the `exporter` key of their front matter (or [metadata](https://www.mkdocs.org/user-guide/writing-your-docs/#meta-data)).
Each option overrides the setting of the configuration with the same name, and options left out keep it:

```yaml
---
author: Jane Doe
description: How to configure the plugin.
tags:
  - configuration
exporter:
  pdf:
    enabled: true
    covers:
      front: covers/release-notes.html.j2
    toc:
      enabled: false
---

# Configuration
```

| Option | Effect | See |
|---|---|---|
| `exporter.pdf.enabled` | `false` leaves the page without a document; `true` gives it one in explicit mode (`formats.pdf.explicit`) | [Choosing pages](../configuration/generating-pdf-documents.md#choosing-pages) |
| `exporter.pdf.covers.enabled` | `false` leaves the page's document without cover pages | [Hiding cover pages](../configuration/generating-pdf-documents.md#hiding-cover-pages) |
| `exporter.pdf.covers.front`, `exporter.pdf.covers.back` | Templates replacing the cover pages of the page, relative to `mkdocs.yml` | [Per-page cover pages](../configuration/generating-pdf-documents.md#per-page-cover-pages) |
| `exporter.pdf.toc.enabled` | `false` leaves out the table of contents of the page's document, `true` gives it one (instead of `formats.pdf.toc.enabled`) | [Table of contents](../configuration/generating-pdf-documents.md#table-of-contents) |
| `exporter.buttons` | Buttons added to the page, besides those of `buttons` | [Adding buttons to a specific page](../configuration/adding-buttons-to-pages.md#adding-buttons-to-a-specific-page) |

Options are checked: a misspelled option, or a value of the wrong type (e.g. `enabled: "no"` instead of `enabled: false`), fails the build with the page's path.
With the `meta` plugin of Material for MkDocs, the options of every page of a directory can be set in its `.meta.yml` file.

The information of documents comes from keys shared with themes and other plugins, outside of `exporter`:

| Key | Effect | See |
|---|---|---|
| `author` | The author of the document (`site_author` by default) | [Document information](../configuration/generating-pdf-documents.md#document-information) |
| `description` | The subject of the document (`site_description` by default) | [Document information](../configuration/generating-pdf-documents.md#document-information) |
| `keywords`, `tags` | The keywords of the document | [Document information](../configuration/generating-pdf-documents.md#document-information) |

Cover templates also receive every key of the front matter, as variables and in `page.meta` (e.g. `page.meta.description`).

## Deprecated keys

Earlier versions read options from top-level keys, which other plugins may use too.
They still work, but log a warning (which fails builds run with `--strict`):

| Deprecated key | Replacement |
|---|---|
| `pdf` | `exporter.pdf.enabled` |
| `covers` | `exporter.pdf.covers.front` and `exporter.pdf.covers.back` |
| `hide: [covers]` | `exporter.pdf.covers.enabled: false` |
| `toc` | `exporter.pdf.toc.enabled` |
| `buttons` | `exporter.buttons` |
| `pdf-icon` | The `icon` of a button in `exporter.buttons` |

When a page has both, the options of `exporter` take precedence.
