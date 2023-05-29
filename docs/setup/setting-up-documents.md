# Setting up documents

## Configuration

First of all, you'll need to register the `mkdocs/exporter/pdf` plugin (**after** the `mkdocs/exporter` one) to your configuration:

```yaml
plugins:
  - mkdocs/exporter
  - mkdocs/exporter/pdf
```

???+ question "Why an additional plugin?"

    **MkDocs Exporter** comes with various plugins in a single package.
  
    This architecture has been chosen to reduce code duplication and maintain a generic base that can be used
    to export your pages to formats other than PDF (although this is the only format currently supported).

    Basically, the `mkdocs/exporter` must always be registered first as it provides a common ground for
    other plugins to use.

## Usage

### Toggle documents generation

The documents generation can be enabled or disabled at any time.  
This feature is especially useful during your development process, when you don't want to slow down your iterations because of document generation.

```yaml
plugins:
  - mkdocs/exporter
  - mkdocs/exporter/pdf:
      enabled: ![MKDOCS_EXPORTER_ENABLED, true]
```

You can now use the `MKDOCS_EXPORTER_ENABLED` environment variable to toggle the PDF generation.

### Setup cover pages

Cover pages can give your PDF documents a professional quality.  
Here is how cover pages are set up for this documentation.

???+ tip "Power! Unlimited Power!"

    The following examples use the [`macros`](https://github.com/fralau/mkdocs_macros_plugin) plugin for *extra powerful* pages.

<div class="page-break"></div>

=== "`mkdocs.yml`"

    ```yaml
    plugins:
      - mkdocs/exporter
      - mkdocs/exporter/pdf:
          stylesheets:
            - resources/stylesheets/pdf.scss
          covers:
            front: resources/templates/covers/front.html.j2
            back: resources/templates/covers/back.html.j2
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs.yml).

=== "`resources/templates/covers/front.html.j2`"

    ```html
    <div class="front-cover">
      <img src="/assets/images/background.png">
      <section>
        <div class="brand">{% raw %}{{ config.site_name }}{% endraw %}</div>
        <div class="title">{% raw %}{{ page.title }}{% endraw %}</div>
      </section>
    </div>
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/templates/covers/front.html.j2).

=== "`resources/templates/covers/back.html.j2`"

    ```html
    <div class="back-cover">
      <section>
        <div class="title">{% raw %}{{ config.site_name }}{% endraw %}</div>
      </section>
    </div>
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/templates/covers/back.html.j2).

=== "`resources/stylesheets/pdf.css`"

    ```scss
    @page {
      size: A4;
      margin: 1.20cm;
    }
    ```

    > :material-file-code: See the full content of this file [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/resources/stylesheets/pdf.scss).

### Increase concurrency

PDF are, by default, generated concurrently which greatly reduces build time.  
You may want to override the default value of **4**, based on your current hardware.

```yaml
plugins:
  - mkdocs/exporter/pdf:
      concurrency: 16
```

With this configuration, up to **16** PDF documents can be generated concurrently.  
As you've guessed, a value of **1** will build PDF documents sequentially.

### Exclude some pages

You may want to prevent a page from generating a PDF document.  
To do so, you can use the `pdf` meta tag on your pages:

```yaml
---
pdf: false
---

# Lorem ipsum dolor sit amet

[...]
```

If you exclude more pages than you include, you may want to  and explicitly define the pages for which PDF documents should be generated.  
We call that the `explicit` mode, it can be enabled in your configuration file:

```yaml
plugins:
  - mkdocs/exporter/pdf:
      explicit: true
```

Only pages with a truthy `pdf` meta tag will see their PDF document generated.

```yaml
---
pdf: true
---

# Lorem ipsum dolor sit amet

[...]
```
