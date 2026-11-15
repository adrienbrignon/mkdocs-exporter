"""A loopback HTTP server exposing a built website to the browser."""

from __future__ import annotations

import importlib.resources
import mimetypes
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import TracebackType
from urllib.parse import unquote, urlsplit

RESERVED = "/__mkdocs_exporter__/"
"""The path under which the server exposes its own assets."""

CONTENT_TYPES = {
    ".css": "text/css",
    ".gif": "image/gif",
    ".html": "text/html",
    ".ico": "image/x-icon",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".js": "text/javascript",
    ".json": "application/json",
    ".mjs": "text/javascript",
    ".otf": "font/otf",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ttf": "font/ttf",
    ".webp": "image/webp",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
}
"""Content types that must not depend on the platform's registry (e.g. Windows)."""


def content_type(path: str) -> str:
    """Guesses the content type of a file."""

    suffix = Path(path).suffix.lower()
    kind = CONTENT_TYPES.get(suffix) or mimetypes.guess_type(path)[0]

    if kind is None:
        return "application/octet-stream"
    if kind.startswith("text/") or kind in ("application/json", "image/svg+xml"):
        return kind + "; charset=utf-8"

    return kind


class Server:
    """Serves a website's directory, plus documents held in memory, on 127.0.0.1.

    Paths are resolved against the website's path prefix first (e.g. `/docs/`), then
    against its root, so that root-absolute paths (`/assets/logo.png`) keep working when
    the website is published under a sub-path.
    """

    def __init__(
        self,
        directory: Path,
        prefix: str = "/",
    ) -> None:
        self.directory = directory.resolve()
        self.prefix = prefix if prefix.endswith("/") else prefix + "/"
        self.documents: dict[str, tuple[bytes, str]] = {}
        self.volatile: set[str] = set()
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

        from mkdocs_exporter.core.resources import js

        for name in ("pdf.js", "book.js"):
            source = importlib.resources.files(js).joinpath(name).read_bytes()
            self.documents[RESERVED + name] = (source, content_type(name))

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

    def publish(self, path: str, content: str | bytes, kind: str = "text/html") -> str:
        """Serves some content from memory at a path relative to the website's root.

        The path may contain a query string, which lets several versions of a page be
        served at once while relative URLs keep resolving against the page's location.
        """

        data = content.encode("utf-8") if isinstance(content, str) else content
        key = self._key(self.prefix + path)

        self.documents[key] = (
            data,
            content_type("x.html") if kind == "text/html" else kind,
        )
        self.volatile.add(key)

        return self.url(path)

    def unpublish(self, path: str) -> None:
        """Stops serving content published with `publish`."""

        key = self._key(self.prefix + path)

        self.documents.pop(key, None)
        self.volatile.discard(key)

    def start(self) -> Server:
        """Starts the server in a background thread."""

        server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler())
        server.daemon_threads = True

        self._server = server
        self._thread = threading.Thread(
            target=server.serve_forever, name="mkdocs-exporter-server", daemon=True
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

    def resolve(self, url: str) -> tuple[bytes, str] | None:
        """Returns the content and content type served at some URL, if any."""

        key = self._key(url)

        if key in self.documents:
            return self.documents[key]

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
                return self._read(file)

        return None

    def _read(self, file: Path) -> tuple[bytes, str]:
        """Reads a file of the website."""

        return file.read_bytes(), content_type(file.name)

    @staticmethod
    def _key(url: str) -> str:
        """The key of a document published in memory."""

        parts = urlsplit(url)
        path = unquote(parts.path)

        return f"{path}?{parts.query}" if parts.query else path

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        server = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def do_GET(self) -> None:
                self._respond(body=True)

            def do_HEAD(self) -> None:
                self._respond(body=False)

            def _respond(self, body: bool) -> None:
                resource = server.resolve(self.path)

                if resource is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return

                data, kind = resource

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", kind)
                self.send_header("Content-Length", str(len(data)))
                cacheable = server._key(self.path) not in server.volatile
                self.send_header(
                    "Cache-Control", "max-age=3600" if cacheable else "no-store"
                )
                self.end_headers()

                if body:
                    self.wfile.write(data)

            def log_message(self, format: str, *args: object) -> None:
                pass

        return Handler
