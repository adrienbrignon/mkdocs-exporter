# Command line

The `mkdocs-exporter` command exports websites built by [Zensical](../how-to/zensical.md) (experimental): run it once the website is built.
With MkDocs and ProperDocs, use the plugin instead: it exports documents while the website is built.

## `mkdocs-exporter build`

Exports the website whose configuration file is found in the current directory (`zensical.toml`, `mkdocs.yml` or `mkdocs.yaml`, in that order), with the options of its `exporter` plugin.

| Option | Effect |
|---|---|
| `-f`, `--config-file FILE` | The configuration file of the website |
| `-s`, `--strict` | Fails when warnings are logged |
| `-v`, `--verbose` | Logs details (the `debug` level) |
| `--help` | Shows the options |

The command exits with the status `1` when the website can't be exported (missing or invalid configuration, invalid front matter, missing browser...), when pages fail to render, or when warnings are logged with `--strict`.

## `mkdocs-exporter`

| Option | Effect |
|---|---|
| `--version` | Shows the version of the plugin |
| `--help` | Shows the commands |
