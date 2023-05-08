# MkDocs Exporter

A highly-configurable plugin for [*MkDocs*](https://github.com/mkdocs/mkdocs) that exports your pages to PDF files.

## Features

- :rocket: **Fast** - PDF documents are generated concurrently!
- :star: **Powerful** - it uses a headless browser and some awesome libraries under the hood to generate PDF files
  - [*Paged.js*](https://github.com/pagedjs/pagedjs) polyfills are included by default ([Paged Media](https://www.w3.org/TR/css-page-3/) and [Generated Content](https://www.w3.org/TR/css-gcpm-3/) CSS modules)
  - [*Sass*](https://sass-lang.com/) support (via [`libsass`](https://github.com/sass/libsass-python)) for your stylesheets
- :paintbrush: **Customizable** - full control over the resulting documents
  - Built for and compatible with [`mkdocs-material`](https://github.com/squidfunk/mkdocs-material)
  - Cover pages with templating support (for instance, with the [`macros`](https://github.com/fralau/mkdocs_macros_plugin) plugin)
  - Define custom scripts and stylesheets to customize your PDF documents
  - Define "buttons" at the top of your documentation pages

## Prerequisites

- Python `>= 3.7`
- MkDocs `>= 1.1`

## Installation

The plugin is hosted on [*PyPI*](https://pypi.org/project/mkdocs-exporter/) and can be installed via `pip` (or your favourite package manager):

```bash
pip install mkdocs-exporter
```

## Usage

Three plugins are currently available:

- `mkdocs/exporter` (*required*): base plugin that must precedes the others
- `mkdocs/exporter/pdf` (*optional*): the plugin that exports your pages as individual PDF documents
- `mkdocs/exporter/extras` (*optional*): provides extra functionalities (buttons, HTML utilities...)

### Example

The following configuration excerpt from `mkdocs.yml` should cover the basic functionalities of this plugin:

```yaml
plugins:
  - mkdocs/exporter
  - mkdocs/exporter/pdf:
      concurrency: 8
      covers:
        front: resources/templates/covers/front.html.j2
        back: resources/templates/covers/back.html.j2
      stylesheets:
        - resources/stylesheets/pdf.scss
  - mkdocs/exporter/extras:
      buttons:
        - title: Download as PDF
          icon: !!python/name:mkdocs_exporter.plugins.pdf.button.icon
          href: !!python/name:mkdocs_exporter.plugins.pdf.button.href
          download: !!python/name:mkdocs_exporter.plugins.pdf.button.download
```

## Roadmap

- Documentation (based on `MkDocs` and featuring this plugin)
- Ensure full compatibility with other themes than `mkdocs-material`
- Combine all pages as one PDF

## License

This project is licensed under the `MIT License (MIT)`, which you can read [here](LICENSE.md).
