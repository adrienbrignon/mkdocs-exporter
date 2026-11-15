from typing import Any, Protocol


class Page(Protocol):
    """A MkDocs page, as seen by button callables.

    Besides MkDocs' own attributes, the exporter sets `formats`: the documents generated
    for the page, by format. For instance, `page.formats["pdf"]` holds the `path` of the
    PDF document on disk and its `url` relative to the website's root.
    """

    title: str
    url: str
    meta: dict[str, Any]
    formats: dict[str, dict[str, Any]]
