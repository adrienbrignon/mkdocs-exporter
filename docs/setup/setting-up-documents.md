# Setting up PDF documents

## Prerequisites

Under-the-hood, this library depends on a web browser controlled by *Playwright* to generate PDF documents.

At the time of writing, *Playwright* supports the following operating systems:

- Python 3.8 or higher
- Windows 10+, Windows Server 2016+ or Windows Subsystem for Linux (WSL)
- macOS 12 Monterey or MacOS 13 Ventura
- Debian 11, Debian 12, Ubuntu 20.04 or Ubuntu 22.04

???+ tip "Your operating system is not supported?"

    You can still use *Docker* to build your documentation from any operating system.  
    Feel free to check out the [Dockerfile](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/Dockerfile) used by this documentation.
  
To install the browser and its required dependencies, run:

```bash
playwright install --with-deps
```

## Configuration

First of all, you'll need to register the `exporter-pdf` plugin (**after** the `exporter` one) to your configuration:

```yaml
plugins:
  - exporter
  - exporter-pdf
```

You can find the configuration reference [here](../reference/configuration/pdf.md).

???+ question "Why multiple plugins?"

    **MkDocs Exporter** comes as various plugins in a single package.
  
    This architecture reduces code duplication and maintains a generic base that can be used to export
    your pages to formats other than PDF (although this is currently the only format supported).

    To sum things up, the `exporter` plugin should always be registered first as it provides a common ground for
    other plugins to rely on.

<div class="page-break"></div>

## Usage

### Toggling documents generation

Document generation can be enabled or disabled at any time.
This feature is particularly useful during your development processes: when you don't want to slow down your iterations because of document generation.

```yaml
plugins:
  - exporter
  - exporter-pdf:
      enabled: ![MKDOCS_EXPORTER_ENABLED, true]
```

With this configuration, the `MKDOCS_EXPORTER_ENABLED` environment variable can be used as a switch for the generation process.

### Setting up cover pages

Cover pages can give your PDF documents a professional quality.  
Here's how cover pages are set up for this documentation.

???+ tip "Power! Unlimited Power!"

    The following examples use the [`macros`](https://github.com/fralau/mkdocs_macros_plugin) plugin for *extra powerful* pages.

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - exporter
      - exporter-pdf:
          stylesheets:
            - resources/stylesheets/pdf.scss
          covers:
            front: resources/templates/covers/front.html.j2
            back: resources/templates/covers/back.html.j2

    [...]
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs.yml).

<div class="page-break"></div>

=== "`resources/templates/covers/front.html.j2`"

    ```html
    <div class="front-cover">
      <img src="/assets/images/background.png">
      <section>
        <div class="brand">{% raw %}{{ config.site_name }}{% endraw %}</div>
        <div class="title">{% raw %}{{ page.title }}{% endraw %}</div>
      </section>
    </div>

    [...]
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/templates/covers/front.html.j2).

=== "`resources/templates/covers/back.html.j2`"

    ```html
    <div class="back-cover">
      <section>
        <div class="title">{% raw %}{{ config.site_name }}{% endraw %}</div>
      </section>
    </div>

    [...]
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/templates/covers/back.html.j2).

=== "`resources/stylesheets/pdf.scss`"

    ```scss
    @page {
      size: A4;
      margin: 1.20cm;
    }

    [...]
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/stylesheets/pdf.scss).

<div class="page-break"></div>

### Increasing concurrency

PDF are, by default, generated concurrently which greatly reduces the overall build time.  
You may want to override the default value of **4**, depending on your hardware.

```yaml
plugins:
  - exporter-pdf:
      concurrency: 16
```

With this configuration, up to **16** PDF documents will be generated concurrently.  
As you've guessed, a value of **1** will force PDF documents to be built sequentially.

### Excluding some pages

You may want to prevent some pages from generating a PDF document.  
To do so, you can use the `pdf` meta tag on your pages:

```yaml
---
pdf: false
---

# Lorem ipsum dolor sit amet

[...]
```

If you exclude more pages than you include, you may want to explicitly define the pages for which PDF documents should be generated.  
This behaviour is called the `explicit` mode, it can be enabled in your configuration file:

```yaml
plugins:
  - exporter-pdf:
      explicit: true
```

With this option, only pages with a truthy `pdf` meta tag will have their corresponding PDF document generated.

```yaml
---
pdf: true
---

# Lorem ipsum dolor sit amet

[...]
```
