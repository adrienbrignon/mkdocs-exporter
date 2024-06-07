---
hide:
  - navigation
---

<div class="mkdocs-exporter" style="display: none;"></div>

# Getting started

## Introduction

[MkDocs Exporter](/) is a plugin for [MkDocs](https://www.mkdocs.org/), it allows you to export your documentation to various formats such as PDF. If you're familiar with Python, you can install the plugin with `pip` (or your favourite package manager).

## Examples

- [__Read__ this documentation in the PDF format](../documentation.pdf)
- [__View__ this page in the PDF format](./index.pdf)

## Prerequisites

- Python `>= 3.9`
- MkDocs `>= 1.4`
- A compatible theme
  - [`material`](https://github.com/squidfunk/mkdocs-material) (:material-star-shooting: *used by this documentation*)
  - [`readthedocs`](https://www.mkdocs.org/user-guide/choosing-your-theme/#readthedocs)

## Installation

You can start by installing the plugin with the package manager of your choice:

```
pip install mkdocs-exporter
```

You can now register the plugin in your configuration file:

```yaml
plugins:
  - exporter
```

Check out the [configuration guides](configuration/generating-pdf-documents) for more details about how to use and configure the plugin.
