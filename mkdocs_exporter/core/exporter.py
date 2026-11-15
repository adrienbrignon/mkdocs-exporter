"""Exports a built website to PDF documents."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from mkdocs_exporter.core.aggregator import Aggregation, aggregate
from mkdocs_exporter.core.browser import Browser
from mkdocs_exporter.core.document import Document, Layout, Site
from mkdocs_exporter.core.renderer import Outcome, Renderer, RenderOptions
from mkdocs_exporter.core.server import Server
from mkdocs_exporter.core.themes import Theme


@dataclass
class Report:
    """The outcome of an export."""

    layouts: dict[str, Layout] = field(default_factory=dict)
    """The layout of each document rendered, by document identifier."""

    failures: list[Outcome] = field(default_factory=list)
    """The documents that could not be rendered."""


class Exporter:
    """Renders the documents of a website and combines them."""

    def __init__(
        self,
        site: Site,
        theme: Theme,
        browser: Browser,
        options: RenderOptions | None = None,
    ) -> None:
        self.site = site
        self.theme = theme
        self.browser = browser
        self.options = options or RenderOptions()

    async def export(
        self, documents: Sequence[Document], aggregations: Sequence[Aggregation] = ()
    ) -> Report:
        """Writes a PDF document for each document, then each aggregated document.

        Aggregations are skipped when a document could not be rendered.
        """

        report = Report()
        server = Server(self.site.directory, self.site.prefix)

        async with self.browser:
            with server:
                renderer = Renderer(
                    self.site, self.theme, self.browser, server, self.options
                )

                for outcome in await renderer.render_all(documents):
                    if outcome.result is None:
                        report.failures.append(outcome)
                        continue

                    if outcome.result.layout is not None:
                        report.layouts[outcome.document.id] = outcome.result.layout

                    _write(
                        self.site.directory / outcome.document.path, outcome.result.pdf
                    )

                if report.failures:
                    return report

                for index, aggregation in enumerate(aggregations):
                    report.failures += await aggregate(
                        renderer,
                        aggregation,
                        report.layouts,
                        self.site,
                        name=f"aggregate-{index}",
                    )

        return report


def _write(path: Path, data: bytes) -> None:
    """Writes a binary file, creating its directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
