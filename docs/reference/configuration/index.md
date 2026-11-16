# Configuration

The options of the plugin, set in `mkdocs.yml` (or in `zensical.toml`, see [Zensical](../../guides/zensical.md)):

```yaml
plugins:
  - exporter:
      formats:
        pdf:
          ...
      buttons:
        - ...
```

The options of PDF documents (`formats.pdf`) are described in [PDF](formats/pdf.md).

::: mkdocs_exporter.config.Config
    options:
      heading: "exporter"

::: mkdocs_exporter.config.ButtonConfig
    options:
      heading: "buttons[]"

::: mkdocs_exporter.config.LoggingConfig
    options:
      heading: "logging"
