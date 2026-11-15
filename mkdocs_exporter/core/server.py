from __future__ import annotations

import importlib.resources
import mimetypes
import threading
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from urllib.parse import unquote, urlsplit

RESERVED = "/__mkdocs_exporter__/"
"""The path under which the server exposes its own assets."""

TYPES = mimetypes.MimeTypes()
"""Content types by extension (Python's defaults: unlike the module's functions, they
don't depend on the platform's registry)."""

for kind, extension in [
    ("text/javascript", ".js"),
    ("text/javascript", ".mjs"),
    ("font/otf", ".otf"),
    ("font/ttf", ".ttf"),
    ("font/woff", ".woff"),
    ("font/woff2", ".woff2"),
    ("image/webp", ".webp"),
]:
    TYPES.add_type(kind, extension)

TEXTUAL = ("application/json", "image/svg+xml")
"""Content types of text, besides `text/*`."""

HTML = "text/html; charset=utf-8"
"""The content type of pages published from memory."""


def content_type(path: str) -> str:
    """The content type of a file."""

    kind = TYPES.guess_type(path)[0] or "application/octet-stream"

    if kind.startswith("text/") or kind in TEXTUAL:
        return kind + "; charset=utf-8"

    return kind


@dataclass(frozen=True)
class Resource:
    """Something served to the browser."""

    data: bytes
    type: str
    cacheable: bool = True
    """May the browser reuse it (pages published from memory change between prints)?"""


class Server:
    """Serves a website's directory, plus pages published from memory, on 127.0.0.1.

    Paths are resolved against the website's path prefix first (e.g. `/docs/`), then
    against its root, so that root-absolute paths (`/assets/logo.png`) keep working when
    the website is published under a sub-path.
    """

    def __init__(self, directory: Path, prefix: str = "/") -> None:
        from mkdocs_exporter.core.resources import js

        self.directory = directory.resolve()
        self.prefix = prefix if prefix.endswith("/") else prefix + "/"
        self.pages: dict[str, bytes] = {}
        self.assets = {
            RESERVED + name: importlib.resources.files(js).joinpath(name).read_bytes()
            for name in ("pdf.js", "book.js")
        }
        self._server: _HttpServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def origin(self) -> str:
        """The server's origin (e.g. `http://127.0.0.1:41234`)."""

        if self._server is None:
            raise RuntimeError("The server is not running")

        host, port = self._server.server_address[:2]

        return f"http://{host!s}:{port}"

    def url(self, path: str) -> str:
        """The absolute URL of a path relative to the website's root."""

        return self.origin + self.prefix + path

    def publish(self, path: str, html: str) -> str:
        """Serves an HTML page from memory at a path relative to the website's root.

        The path may contain a query string, which lets several versions of a page be
        served at once while relative URLs keep resolving against the page's location.
        """

        self.pages[_key(self.prefix + path)] = html.encode("utf-8")

        return self.url(path)

    def unpublish(self, path: str) -> None:
        """Stops serving a page published with `publish`."""

        self.pages.pop(_key(self.prefix + path), None)

    def resolve(self, url: str) -> Resource | None:
        """What is served at a URL, if anything."""

        key = _key(url)

        if (page := self.pages.get(key)) is not None:
            return Resource(page, HTML, cacheable=False)
        if (asset := self.assets.get(key)) is not None:
            return Resource(asset, content_type(key))
        if (file := self.file(url)) is not None:
            return Resource(file.read_bytes(), content_type(file.name))

        return None

    def file(self, url: str) -> Path | None:
        """The file of the website served at a URL, if any."""

        path = unquote(urlsplit(url).path)
        candidates = [path.lstrip("/")]

        if path.startswith(self.prefix):
            candidates.insert(0, path[len(self.prefix) :])

        for candidate in candidates:
            file = (self.directory / candidate).resolve()

            if not file.is_relative_to(self.directory):
                continue
            if file.is_dir():
                file = file / "index.html"
            if file.is_file():
                return file

        return None

    def start(self) -> Server:
        """Starts the server in a background thread."""

        self._server = _HttpServer(self)
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            name="mkdocs-exporter-server",
            daemon=True,
        )
        self._thread.start()

        return self

    def stop(self) -> None:
        """Stops the server."""

        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join()

        self._server = None
        self._thread = None

    def __enter__(self) -> Server:
        return self.start()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()


class _HttpServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, site: Server) -> None:
        super().__init__(("127.0.0.1", 0), _Handler)
        self.site = site


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: _HttpServer

    def do_GET(self) -> None:
        self._respond(body=True)

    def do_HEAD(self) -> None:
        self._respond(body=False)

    def _respond(self, body: bool) -> None:
        resource = self.server.site.resolve(self.path)

        if resource is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", resource.type)
        self.send_header("Content-Length", str(len(resource.data)))
        self.send_header(
            "Cache-Control", "max-age=3600" if resource.cacheable else "no-store"
        )
        self.end_headers()

        if body:
            self.wfile.write(resource.data)

    def log_message(self, format: str, *args: object) -> None:
        pass


def _key(url: str) -> str:
    """The path and query of a URL (the key of what is served from memory)."""

    parts = urlsplit(url)
    path = unquote(parts.path)

    return f"{path}?{parts.query}" if parts.query else path
