# MkDocs Exporter

<div>
  <a href="https://pypi.org/project/mkdocs-exporter">
    <img src="https://img.shields.io/pypi/v/mkdocs-exporter?color=blue">
  </a>
  <a href="https://pypi.org/project/mkdocs-exporter">
    <img src="https://img.shields.io/pypi/pyversions/mkdocs-exporter?color=blue">
  </a>
  <a href="https://pypi.org/project/mkdocs-exporter">
    <img src="https://img.shields.io/pypi/dm/mkdocs-exporter?color=blue">
  </a>
  <a href="https://github.com/adrienbrignon/mkdocs-exporter/blob/master/LICENSE">
    <img align="right" src="https://img.shields.io/github/license/adrienbrignon/mkdocs-exporter?color=white">
  </a>
</div>
<a href="https://adrienbrignon.github.io/mkdocs-exporter/getting-started/">
  <img src="https://github.com/adrienbrignon/mkdocs-exporter/assets/10183277/85c768f6-fe27-43a1-998c-ac89e926cba1" align="right" width="350">
</a>
<br />

A highly configurable plugin for [*MkDocs*](https://github.com/mkdocs/mkdocs) that exports your pages as PDF documents.  
Additionally, it can combine your entire documentation into a single PDF file.

- [Documentation](https://adrienbrignon.github.io/mkdocs-exporter)
- [PyPI](https://pypi.org/project/mkdocs-exporter)
- [Examples](https://adrienbrignon.github.io/mkdocs-exporter/examples/)

## Features

- 🚀 **Fast** - documents are rendered concurrently
- 📚 **Books** - combine pages into PDF documents with bookmarks, a table of contents and working links
- 🎨 **Customizable** - full control over the resulting documents
  - [Cover pages](https://adrienbrignon.github.io/mkdocs-exporter/configuration/generating-pdf-documents/#cover-pages) written as Jinja templates
  - [Headers and footers](https://adrienbrignon.github.io/mkdocs-exporter/configuration/headers-and-footers/) with page numbers
  - Custom [stylesheets, scripts and hooks](https://adrienbrignon.github.io/mkdocs-exporter/configuration/customizing-documents/)
  - [Buttons](https://adrienbrignon.github.io/mkdocs-exporter/configuration/adding-buttons-to-pages/) at the top of your pages (e.g. to download the page as PDF)
  - Dedicated support for the [`material`](https://github.com/squidfunk/mkdocs-material) and [`readthedocs`](https://www.mkdocs.org/user-guide/choosing-your-theme/#readthedocs) themes, check out [sample PDF documents](https://adrienbrignon.github.io/mkdocs-exporter/examples/#themes)
- ⭐ **Powerful** - documents are printed by Chromium, driven by [*Playwright*](https://github.com/microsoft/playwright-python), with [CSS Paged Media](https://www.w3.org/TR/css-page-3/) support

## Prerequisites

- Python `>= 3.11.5`
- MkDocs `>= 1.6, < 2` (or [ProperDocs](https://github.com/ProperDocs/properdocs))

MkDocs 2.0 doesn't support plugins and Zensical ignores MkDocs plugins: a standalone command, able to export any built website, is planned.

## Installation

The plugin is hosted on [*PyPI*](https://pypi.org/project/mkdocs-exporter/) and can be installed via `pip` (or your favourite package manager), along with the browser it uses:

```bash
pip install "mkdocs-exporter>=7.0.0rc1"
playwright install --with-deps --only-shell chromium
```

Version 7 is a release candidate: until 7.0.0 is released, `pip install mkdocs-exporter` (without a version) installs 6.2.0.

Upgrading from v6? Read the [migration guide](https://adrienbrignon.github.io/mkdocs-exporter/migration/v7/).

## Usage

The following configuration (adapted from the [`mkdocs.yml`](./mkdocs.yml) file used by this documentation) covers the main features of this plugin:

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          enabled: !ENV [MKDOCS_EXPORTER_PDF, true]
          concurrency: 8
          stylesheets:
            - resources/stylesheets/pdf.css
          covers:
            front: resources/templates/covers/front.html.j2
            back: resources/templates/covers/back.html.j2
          footer:
            right: "Page {page} of {pages}"
          books:
            - output: documentation.pdf
              covers: front
              toc:
                enabled: true
```

Check out the [examples](https://adrienbrignon.github.io/mkdocs-exporter/examples/): documents generated from a small website (with cover pages, tables of contents, headers and footers...), with their configuration ([`examples/`](examples)).

## Roadmap

- [x] Combine all pages into a single PDF document (✅ released in [`v6.0.0`](https://github.com/adrienbrignon/mkdocs-exporter/releases/tag/v6.0.0))
- [x] Bookmarks, table of contents and links in combined documents (✅ released in `v7.0.0`)
- [ ] A standalone command exporting any built website (Zensical, MkDocs 2.0...)
- [ ] Create a *GitHub* action that includes all dependencies to build the documentation and generate PDF documents

Feel free to request additional features by submitting an issue or contributing through a pull request.

## Contributing

We welcome contributions from the community to enhance MkDocs Exporter.  
Whether you want to report a bug, suggest a feature, improve the documentation, or contribute code, your help is appreciated!
See [`AGENTS.md`](AGENTS.md) for how the project is organized, built and tested.

## License

This project is licensed under the `MIT License (MIT)`, which you can read [here](LICENSE).
