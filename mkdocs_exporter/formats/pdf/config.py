from mkdocs.config import config_options as c
from mkdocs.config.base import Config as BaseConfig

from mkdocs_exporter.core import margins
from mkdocs_exporter.core.books import COVER_MODES, START_MODES


class Stylesheet(c.File):
    """A stylesheet (plain CSS only)."""

    def run_validation(self, value: object) -> str:
        """Validates the stylesheet's location."""

        path = super().run_validation(value)

        if path.lower().endswith((".scss", ".sass")):
            raise c.ValidationError(
                f"Sass stylesheets are no longer supported ('{value}'), "
                "use plain CSS instead. "
                "See https://adrienbrignon.github.io/mkdocs-exporter/guides/migrating-to-v7/"
            )

        return path


class PositiveInteger(c.Type[int]):
    """A strictly positive integer."""

    def __init__(self, default: int | None = None) -> None:
        super().__init__(int, default=default)

    def run_validation(self, value: object) -> int:
        """Validates the value."""

        number = super().run_validation(value)

        if number < 1:
            raise c.ValidationError(f"Expected a positive integer, got {number}")

        return number


class MarginText(c.Type[str]):
    """The text of a header or a footer (with placeholders)."""

    def __init__(self) -> None:
        super().__init__(str)

    def run_validation(self, value: object) -> str:
        """Validates the text's placeholders."""

        text = super().run_validation(value)

        try:
            margins.validate(text)
        except ValueError as error:
            raise c.ValidationError(str(error)) from error

        return text


class MarginsConfig(BaseConfig):
    """A header or a footer: texts with placeholders such as `{page}` / `{pages}`."""

    left = c.Optional(MarginText())
    """The text on the left."""

    center = c.Optional(MarginText())
    """The text in the center."""

    right = c.Optional(MarginText())
    """The text on the right."""


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


class CacheConfig(BaseConfig):
    """The cache's configuration."""

    enabled = c.Type(bool, default=True)
    """Should documents be reused while their page and resources are unchanged?"""

    directory = c.Type(str, default=".cache/plugin/exporter")
    """The cache's directory (relative to the configuration file)."""


class TocConfig(BaseConfig):
    """A table of contents (of a document's headings, or of a book)."""

    enabled = c.Type(bool, default=False)
    """Should a table of contents be inserted after the (first) front cover?"""

    title = c.Type(str, default="Table of contents")
    """The title of the table of contents."""

    depth = PositiveInteger(default=2)
    """The deepest level of headings listed (in books, 1 lists pages only)."""

    template = c.Optional(c.File(exists=True))
    """A Jinja template replacing the default one (variables: `title`, `entries`)."""


class BookConfig(BaseConfig):
    """A book: pages combined into a single document."""

    enabled = c.Type(bool, default=True)
    """Is the book generated?"""

    output = c.Type(str, default="book.pdf")
    """The path of the document, relative to the website's root."""

    metadata = c.Type(dict, default={})
    """Information about the document (`title`, `author`, `subject`, `keywords`)."""

    covers = c.Choice(COVER_MODES, default="all")
    """The cover pages kept (`all`, `none`, `limits`, `book`, `front` or `back`)."""

    include = c.ListOfItems(c.Type(str), default=["*"])
    """Patterns of the source paths of the pages to combine (`*` matches any text)."""

    exclude = c.ListOfItems(c.Type(str), default=[])
    """Patterns of the source paths of the pages to leave out."""

    start = c.Choice(START_MODES, default="any")
    """`odd` to start every page on an odd (right-hand) page, inserting blank pages."""

    outline = c.Type(int, default=3)
    """The depth of bookmarks: 0 for none, 1 for pages, 2 to add their `h2` headings..."""

    tagged = c.Type(bool, default=True)
    """Is the document tagged (its structure described, for screen readers)? Tagging
    makes documents about half as large again."""

    toc = c.SubConfig(TocConfig)
    """The table of contents."""


class AggregatorConfig(BookConfig):
    """A single book (deprecated: use `books`)."""

    enabled = c.Type(bool, default=False)
    """Is the book generated?"""

    output = c.Type(str, default="combined.pdf")
    """The path of the document, relative to the website's root."""


class Config(BaseConfig):
    """The plugin's configuration."""

    enabled = c.Type(bool, default=True)
    """Is the generator enabled?"""

    serve = c.Type(bool, default=False)
    """Should documents be generated while serving the website (`mkdocs serve`)?"""

    explicit = c.Type(bool, default=False)
    """Should pages specify explicitly that they should be rendered as PDF?"""

    title = c.Type(bool, default=False)
    """Should the page's title be inserted at the top of documents lacking a `h1`?"""

    concurrency = c.Optional(PositiveInteger())
    """The number of documents rendered at once (twice the number of CPUs, up to 8, by
    default)."""

    stylesheets = c.ListOfItems(Stylesheet(exists=True), default=[])
    """A list of custom stylesheets to apply before rendering documents."""

    scripts = c.ListOfItems(c.File(exists=True), default=[])
    """A list of custom scripts to inject before rendering documents."""

    covers = c.SubConfig(CoversConfig)
    """The document's cover pages."""

    header = c.SubConfig(MarginsConfig)
    """The header of pages (`{site_name}`, `{page_title}`, `{section}`, `{page}`, `{pages}`)."""

    footer = c.SubConfig(MarginsConfig)
    """The footer of pages (same placeholders as the header)."""

    browser = c.SubConfig(BrowserConfig)
    """The browser's configuration."""

    cache = c.SubConfig(CacheConfig)
    """The cache of documents."""

    url = c.Optional(c.Type(str))
    """The URL replacing the website's root in links (defaults to `site_url`)."""

    toc = c.SubConfig(TocConfig)
    """The table of contents of each document (its headings)."""

    books = c.ListOfItems(c.SubConfig(BookConfig), default=[])
    """Books: pages combined into single documents."""

    aggregator = c.SubConfig(AggregatorConfig)
    """A single book (deprecated: use `books`)."""
