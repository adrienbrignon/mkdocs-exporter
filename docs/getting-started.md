---
hide:
  - navigation
---

# Getting started

## Introduction

[MkDocs Exporter](/) is a plugin for [MkDocs](https://www.mkdocs.org/), it allows you to export your documentation to various formats such as PDF. If you're familiar with Python, you can install the plugin with `pip` (or your favourite package manager).

???+ tip "Did you know?"

    This documentation website features the plugin, meaning that you can download this page as a PDF document and read it offline!

    Try this out by clicking the download button at the top of this page (or you can directly head [here](./getting-started.pdf){:target="_blank"}).



## Installation

You can start by installing the plugin with the package manager of your choice:

```
pip install mkdocs-exporter
```

You can now register the plugin in your configuration file:

```yaml
plugins:
  - mkdocs/exporter
```

Check out the [setup guides](/setup) for more details about how to use and configure the plugin.
