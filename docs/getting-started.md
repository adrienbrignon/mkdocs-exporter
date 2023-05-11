# Getting started

[MkDocs Exporter](/) is a plugin for [MkDocs](https://www.mkdocs.org/), it allows you to export your documentation to various formats such as PDF. If you're familiar with Python, you can install the plugin with `pip` (or your favourite package manager).

???+ tip "Did you know?"

    This documentation website features the plugin, meaning that you can download this page as a PDF document and read it offline!

    Try this out by clicking the download button at the top of this page (or you can directly head [here](/getting-started/getting-started.pdf){:target="_blank"}).

## Installation

You can start by installing the plugin with the package manager of your choice:

```
pip install mkdocs-exporter
```

If you plan on using this plugin to generate PDF documents, you'll also need to install a browser and its dependencies.  
As this project uses [Playwright](https://github.com/microsoft/playwright) under the hood, the installation is a breeze:

```
playwright install --with-deps
```
