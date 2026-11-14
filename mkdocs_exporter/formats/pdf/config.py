from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig

from mkdocs_exporter.core.aggregator import COVER_MODES, START_MODES


class Stylesheet(c.File):
    """A stylesheet (plain CSS only)."""

    def run_validation(self, value: object) -> str:
        """Validates the stylesheet's location."""

        path = super().run_validation(value)

        if path.lower().endswith((".scss", ".sass")):
            raise c.ValidationError(
                f"Sass stylesheets are no longer supported ('{value}'), "
                "use plain CSS instead. "
                "See https://adrienbrignon.github.io/mkdocs-exporter/migration/v7/"
            )

        return path


class PositiveInteger(c.Type[int]):
    """A strictly positive integer."""

    def __init__(self, default: int) -> None:
        super().__init__(int, default=default)

    def run_validation(self, value: object) -> int:
        """Validates the value."""

        number = super().run_validation(value)

        if number < 1:
            raise c.ValidationError(f"Expected a positive integer, got {number}")

        return number


class BrowserConfig(BaseConfig):
    """The browser's configuration."""

    debug = c.Type(bool, default=False)
    """Should console messages sent to the browser be logged?"""

    headless = c.Type(bool, default=True)
    """Should the browser start in headless mode?"""

    timeout = PositiveInteger(default=60_000)
    """The time (in milliseconds) given to each document to render."""

    delay = c.Type(int, default=0)
    """Extra time (in milliseconds) given to scripts before paginating documents."""

    channel = c.Optional(c.Type(str))
    """The browser distribution channel (e.g. `chrome`, `msedge`), Chromium by default."""

    args = c.ListOfItems(c.Type(str), default=[])
    """Extra arguments to pass to the browser."""


class CoversConfig(BaseConfig):
    """The cover's configuration."""

    front = c.Optional(c.File(exists=True))
    """The front cover template location."""

    back = c.Optional(c.File(exists=True))
    """The back cover template location."""


class TocConfig(BaseConfig):
    """The table of contents of an aggregated document."""

    enabled = c.Type(bool, default=False)
    """Should a table of contents be inserted after the first document's front cover?"""

    title = c.Type(str, default="Table of contents")
    """The title of the table of contents."""

    depth = PositiveInteger(default=2)
    """The depth of entries: 1 for pages only, 2 to add their second-level headings..."""

    template = c.Optional(c.File(exists=True))
    """A Jinja template replacing the default one (variables: `title`, `entries`)."""


class AggregatorConfig(BaseConfig):
    """The aggregator's configuration."""

    enabled = c.Type(bool, default=True)
    """Is the aggregator enabled?"""

    output = c.Type(str, default="combined.pdf")
    """The aggregated PDF document output file path."""

    metadata = c.Type(dict, default={})
    """Some metadata to append to the PDF document."""

    covers = c.Choice(COVER_MODES, default="all")
    """The behavior of cover pages."""

    include = c.ListOfItems(c.Type(str), default=["*"])
    """Patterns of the source paths of the pages to aggregate (`*` matches any text)."""

    exclude = c.ListOfItems(c.Type(str), default=[])
    """Patterns of the source paths of the pages not to aggregate."""

    start = c.Choice(START_MODES, default="any")
    """`odd` to start every page on an odd (right-hand) page, inserting blank pages."""

    outline = c.Type(int, default=3)
    """The depth of bookmarks: 0 for none, 1 for pages, 2 to add their `h2` headings..."""

    toc = c.SubConfig(TocConfig)
    """The table of contents."""


class SingleAggregatorConfig(AggregatorConfig):
    """The configuration of the main aggregated document."""

    enabled = c.Type(bool, default=False)
    """Is the aggregator enabled?"""


class Config(BaseConfig):
    """The plugin's configuration."""

    enabled = c.Type(bool, default=True)
    """Is the generator enabled?"""

    serve = c.Type(bool, default=False)
    """Should documents be generated while serving the website (`mkdocs serve`)?"""

    explicit = c.Type(bool, default=False)
    """Should pages specify explicitly that they should be rendered as PDF?"""

    concurrency = PositiveInteger(default=4)
    """The maximum number of concurrent PDF generation tasks."""

    stylesheets = c.ListOfItems(Stylesheet(exists=True), default=[])
    """A list of custom stylesheets to apply before rendering documents."""

    scripts = c.ListOfItems(c.File(exists=True), default=[])
    """A list of custom scripts to inject before rendering documents."""

    covers = c.SubConfig(CoversConfig)
    """The document's cover pages."""

    browser = c.SubConfig(BrowserConfig)
    """The browser's configuration."""

    url = c.Optional(c.Type(str))
    """The URL replacing the website's root in links (defaults to `site_url`)."""

    aggregator = c.SubConfig(SingleAggregatorConfig)
    """The aggregated document combining pages (shorthand for a single aggregator)."""

    aggregators = c.ListOfItems(c.SubConfig(AggregatorConfig), default=[])
    """Aggregated documents combining pages."""
