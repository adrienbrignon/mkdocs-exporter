# Extras

The configuration of the `exporter-extras` plugin.

## Schemas

You can find the source code of the following schemas [here](https://github.com/adrienbrignon/mkdocs-exporter/blob/master/mkdocs_exporter/plugins/extras/config.py).

### `Configuration`

| Name                 | Type                                 | Default  | Description                                                  |
|----------------------|--------------------------------------|----------|--------------------------------------------------------------|
| `enabled`            | `bool`                               | `true`   | Should the plugin be enabled?                                |
| `buttons`            | <code>list[[Button](#button)]</code> |          | The custom buttons to define.                                |

### `Button`

| Name                 | Type                                 | Default  | Description                                                  |
|----------------------|--------------------------------------|----------|--------------------------------------------------------------|
| `enabled`            | `bool | Callable`                    | `true`   | Is this button enabled (visible)?                            |
| `title`              | `str | Callable`                     |          | The button's title.                                          |
| `icon`               | `str | Callable`                     |          | The button's icon.                                           |
| `attributes`         | `dict | Callable`                    |          | Custom HTML attributes to apply to the button.               |

## Example

```yaml
plugins:
  - exporter-extras:
      buttons:
        - title: Download as PDF
          icon: material-file-download-outline
          enabled: !!python/name:mkdocs_exporter.plugins.pdf.button.enabled
          attributes:
            href: !!python/name:mkdocs_exporter.plugins.pdf.button.href
            download: !!python/name:mkdocs_exporter.plugins.pdf.button.download
```
