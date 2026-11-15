"""Tests of the loopback server."""

from pathlib import Path
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from mkdocs_exporter.core.server import RESERVED, Server


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

    assert server.resolve("/docs/") == (b"home", "text/html; charset=utf-8")
    assert server.resolve("/docs/guide/")[0] == b"guide"  # type: ignore[index]


def test_resolves_root_absolute_paths(site: Path) -> None:
    assert Server(site, "/docs/").resolve("/guide/index.html")[0] == b"guide"  # type: ignore[index]


def test_refuses_paths_outside_the_site(site: Path) -> None:
    server = Server(site, "/")

    assert server.resolve("/../secret.txt") is None
    assert server.resolve("/%2e%2e/secret.txt") is None
    assert server.resolve("/missing.html") is None


def test_serves_bundled_assets(site: Path) -> None:
    content, kind = Server(site, "/").resolve(RESERVED + "pdf.js")  # type: ignore[misc]

    assert b"__MKDOCS_EXPORTER__" in content
    assert kind.startswith("text/javascript")


def test_serves_published_documents_over_http(site: Path) -> None:
    with Server(site, "/docs/") as server:
        url = server.publish("guide/?pass=1", "<p>printed</p>")

        assert url == server.origin + "/docs/guide/?pass=1"
        assert urlopen(url).read() == b"<p>printed</p>"  # noqa: S310
        assert urlopen(server.url("guide/")).read() == b"guide"  # noqa: S310

        server.unpublish("guide/?pass=1")

        with pytest.raises(HTTPError):
            urlopen(server.origin + "/missing")  # noqa: S310
