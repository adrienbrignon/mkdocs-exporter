from __future__ import annotations

import logging
from pathlib import Path

import click
from mkdocs.exceptions import MkDocsException

from mkdocs_exporter.logging import LOGGER, Logger
from mkdocs_exporter.standalone.export import export
from mkdocs_exporter.standalone.project import ProjectError, load

logger = Logger()


class _Counter(logging.Handler):
    """Counts the warnings (and errors) logged."""

    def __init__(self) -> None:
        super().__init__(logging.WARNING)

        self.count = 0

    def emit(self, record: logging.LogRecord) -> None:
        self.count += 1


@click.group()
@click.version_option(package_name="mkdocs-exporter")
def main() -> None:
    """Exports documentation websites to PDF."""


@main.command()
@click.option(
    "-f",
    "--config-file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="The configuration file of the website (zensical.toml or mkdocs.yml).",
)
@click.option("-s", "--strict", is_flag=True, help="Fail when warnings are logged.")
@click.option("-v", "--verbose", is_flag=True, help="Log details.")
def build(config_file: Path | None, strict: bool, verbose: bool) -> None:
    """Exports a website built by Zensical (experimental).

    Run it once the website is built: it writes the PDF documents into the built
    website, with the options of `[project.plugins.exporter]` in `zensical.toml`, or of
    the `exporter` plugin in `mkdocs.yml`.
    """

    output = logging.StreamHandler()
    output.setFormatter(logging.Formatter("%(levelname)-7s -  %(message)s"))
    counter = _Counter()
    level = LOGGER.level

    LOGGER.addHandler(output)
    LOGGER.addHandler(counter)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)

    try:
        logger.info("Exporting the website (experimental)...")

        project = load(config_file)

        if project.options.logging.level and not verbose:
            LOGGER.setLevel(project.options.logging.level.upper())

        failures = export(project)
    except (ProjectError, MkDocsException) as error:
        raise click.ClickException(str(error)) from error
    finally:
        LOGGER.removeHandler(output)
        LOGGER.removeHandler(counter)
        LOGGER.setLevel(level)

    if failures:
        details = "\n".join(f"- {o.document.id}: {o.error}" for o in failures)

        raise click.ClickException(f"Failed to render pages:\n{details}")
    if strict and counter.count:
        raise click.ClickException(
            f"Aborted with {counter.count} warning(s) in strict mode"
        )
