from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from mkdocs_exporter.core.server import RESERVED, Resource, Server, content_type


@pytest.fixture
def site(tmp_path: Path) -> Path:
    (tmp_path / "site" / "guide").mkdir(parents=True)
    (tmp_path / "site" / "index.html").write_text("home")
    (tmp_path / "site" / "guide" / "index.html").write_text("guide")
    (tmp_path / "site" / "style.css").write_text("a:nth-child(2n+1){}")
    (tmp_path / "secret.txt").write_text("secret")

    return tmp_path / "site"


def test_resolves_paths_under_the_prefix(site: Path) -> None:
    server = Server(site, "/docs/")

    assert server.resolve("/docs/") == Resource(b"home", "text/html; charset=utf-8")
    assert server.resolve("/docs/guide/") == Resource(
        b"guide", "text/html; charset=utf-8"
    )


def test_resolves_root_absolute_paths(site: Path) -> None:
    resource = Server(site, "/docs/").resolve("/guide/index.html")

    assert resource is not None
    assert resource.data == b"guide"


def test_refuses_paths_outside_the_site(site: Path) -> None:
    server = Server(site, "/")

    assert server.resolve("/../secret.txt") is None
    assert server.resolve("/%2e%2e/secret.txt") is None
    assert server.resolve("/missing.html") is None


def test_serves_bundled_assets(site: Path) -> None:
    resource = Server(site, "/").resolve(RESERVED + "pdf.js")

    assert resource is not None
    assert b"__MKDOCS_EXPORTER__" in resource.data
    assert resource.type == "text/javascript; charset=utf-8"


def test_serves_published_documents_over_http(site: Path) -> None:
    with Server(site, "/docs/") as server:
        url = server.publish("guide/?pass=1", "<p>printed</p>")

        assert url == server.origin + "/docs/guide/?pass=1"
        assert urlopen(url).read() == b"<p>printed</p>"  # noqa: S310
        assert urlopen(server.url("guide/")).read() == b"guide"  # noqa: S310

        server.unpublish("guide/?pass=1")

        with pytest.raises(HTTPError):
            urlopen(server.origin + "/missing")  # noqa: S310


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("page.html", "text/html; charset=utf-8"),
        ("style.css", "text/css; charset=utf-8"),
        ("script.js", "text/javascript; charset=utf-8"),
        ("module.mjs", "text/javascript; charset=utf-8"),
        ("search.json", "application/json; charset=utf-8"),
        ("logo.svg", "image/svg+xml; charset=utf-8"),
        ("photo.webp", "image/webp"),
        ("font.woff2", "font/woff2"),
        ("font.ttf", "font/ttf"),
        ("archive.unknown", "application/octet-stream"),
    ],
)
def test_content_types(name: str, expected: str) -> None:
    assert content_type(name) == expected


def test_only_files_may_be_cached(site: Path) -> None:
    with Server(site, "/") as server:
        page = urlopen(server.publish("guide/?pass=1", "<p>printed</p>"))  # noqa: S310
        file = urlopen(server.url("style.css"))  # noqa: S310

        assert page.headers["Cache-Control"] == "no-store"
        assert page.headers["Content-Type"] == "text/html; charset=utf-8"
        assert file.headers["Cache-Control"] == "max-age=3600"
        assert file.headers["Content-Type"] == "text/css; charset=utf-8"
