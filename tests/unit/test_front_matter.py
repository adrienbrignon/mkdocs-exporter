from typing import Any

import pytest

from mkdocs_exporter.front_matter import FrontMatterError, parse


def summary(meta: dict[str, Any]) -> dict[str, Any]:
    """The options a front matter gives (unset options are left out)."""

    options = parse(meta).options
    pdf = options.pdf
    values = {
        "pdf": pdf.enabled,
        "toc": pdf.toc.enabled,
        "covers": pdf.covers.enabled,
        "front": pdf.covers.front,
        "back": pdf.covers.back,
        "buttons": len(options.buttons) or None,
    }

    return {key: value for key, value in values.items() if value is not None}


@pytest.mark.parametrize(
    ("meta", "expected"),
    [
        ({"pdf": "true"}, {"pdf": True}),
        ({"pdf": 0}, {"pdf": False}),
        ({"toc": None}, {"toc": False}),
        ({"covers": None}, {}),
        ({"covers": "front.html"}, {}),
        (
            {"covers": {"front": "front.html", "back": "", "other": "x"}},
            {"front": "front.html"},
        ),
        ({"hide": "covers"}, {"covers": False}),
        ({"hide": ["toc", "covers"]}, {"covers": False}),
        ({"hide": True}, {}),
        ({"buttons": [{"title": "T", "icon": "i"}]}, {"buttons": 1}),
    ],
)
def test_deprecated_keys_keep_their_meaning(
    meta: dict[str, Any], expected: dict[str, Any]
) -> None:
    assert summary(meta) == expected


def test_deprecated_keys_are_reported() -> None:
    meta = {"pdf": True, "hide": ["toc", "covers"], "pdf-icon": "x", "title": "T"}

    assert parse(meta).deprecated == ["pdf", "hide", "pdf-icon"]
    assert parse({"hide": ["toc"]}).deprecated == []


def test_the_exporter_key_is_merged_over_deprecated_keys() -> None:
    meta = {
        "pdf": False,
        "covers": {"front": "old.html", "back": "back.html"},
        "exporter": {"pdf": {"enabled": True, "covers": {"front": "new.html"}}},
    }

    assert summary(meta) == {"pdf": True, "front": "new.html", "back": "back.html"}


def test_pages_without_options() -> None:
    assert summary({"title": "Title", "tags": ["a"]}) == {}
    assert summary({"exporter": None}) == {}


@pytest.mark.parametrize(
    ("exporter", "message"),
    [
        ({"pdf": {"enable": False}}, "exporter.pdf: Sub-option 'enable'"),
        ({"pdf": {"enabled": "no"}}, "exporter.pdf: Sub-option 'enabled'"),
        ({"pdf": {"toc": True}}, "exporter.pdf: Sub-option 'toc'"),
        ({"typo": 1}, "exporter.typo"),
        ({"buttons": [{"icon": "i"}]}, "exporter.buttons: Sub-option 'title'"),
        (True, "expected a mapping of options"),
    ],
)
def test_invalid_options_are_rejected(exporter: Any, message: str) -> None:
    with pytest.raises(FrontMatterError, match=message):
        parse({"exporter": exporter})
