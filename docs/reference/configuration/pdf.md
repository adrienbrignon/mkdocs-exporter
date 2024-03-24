# PDF

The configuration of the `exporter-pdf` plugin.

## Schemas

You can find the source code of the following schemas [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs_exporter/plugins/pdf/config.py).

### `Configuration`

| Name                 | Type                                 | Default  | Description                                                          |
|----------------------|--------------------------------------|----------|----------------------------------------------------------------------|
| `enabled`            | `bool`                               | `true`   | Should the plugin be enabled?                                        |
| `explicit`           | `bool`                               | `false`  | Should pages specify explicitly that they should be rendered as PDF? |
| `concurrency`        | `int`                                | `4`      | The maximum number of concurrent PDF generation tasks.               |
| `stylesheets`        | `list[str]`                          |          | A list of custom stylesheets to apply before rendering documents.    |
| `scripts`            | `list[str]`                          |          | A list of custom scripts to inject before rendering documents.       |
| `covers`             | <code>[Covers](#covers)</code>       |          | The document's cover pages.                                          |
| `browser`            | <code>[Browser](#browser)</code>     |          | The browser's configuration.                                         |
| `url`                | `str`                                |          | The base URL that'll be prefixed to links with a relative path.      |

### `Covers`

| Name                 | Type                                 | Default  | Description                                                       |
|----------------------|--------------------------------------|----------|-------------------------------------------------------------------|
| `front`              | `str`                                |          | The front cover template location.                                |
| `back`               | `str`                                |          | The back cover template location.                                 |

### `Browser`

| Name                 | Type                                 | Default  | Description                                                       |
|----------------------|--------------------------------------|----------|-------------------------------------------------------------------|
| `debug`              | `bool`                               | `false`  | Should console messages sent to the browser be logged?            |
| `headless`           | `bool`                               | `true`   | Should the browser start in headless mode?                        |
| `timeout`            | `int`                                | `60000`  | The timeout (in milliseconds) when waiting for the PDF to render. |

## Example

```yaml
plugins:
  - exporter-pdf:
      concurrency: 8
      enabled: !ENV [MKDOCS_EXPORTER_PDF, true]
      stylesheets:
        - resources/stylesheets/pdf.scss
      covers:
        front: resources/templates/covers/front.html.j2
        back: resources/templates/covers/back.html.j2
      browser:
        debug: false
        headless: true
```
