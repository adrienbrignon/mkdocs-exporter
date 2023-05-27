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
  - mkdocs/exporter/pdf:
      enabled: ![MKDOCS_EXPORTER_ENABLED, true]
```

You can now use the `MKDOCS_EXPORTER_ENABLED` environment variable to toggle the PDF generation.

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

Sometimes, you may want to prevent a page from being converted to a PDF document.  
You can use the `pdf` meta tag on your page to do so:

```yaml
---
pdf: false
---

# Lorem ipsum dolor sit amet

[...]
```

If you exclude more pages than you include, you can take the problem the other way around and explicitly define the pages for which PDF documents should be generated.  
We call that the `explicit` mode, it can be enabled in your configuration file:

```yaml
plugins:
  - mkdocs/exporter/pdf:
      explicit: true
```

Only pages with a truthy value in the `pdf` meta tag will have a PDF document generated.

```yaml
---
pdf: true
---

# Lorem ipsum dolor sit amet

[...]
```
