from mkdocs_exporter.helpers import resolve


def test_resolve_returns_plain_values() -> None:
    assert resolve("value") == "value"
    assert resolve(None) is None


def test_resolve_calls_callables_with_arguments() -> None:
    assert resolve(lambda page: page.upper(), page="index") == "INDEX"


def test_resolve_recurses_into_containers() -> None:
    value = {"title": lambda page: page, "items": [1, lambda page: page * 2]}

    assert resolve(value, page="a") == {"title": "a", "items": [1, "aa"]}


def test_resolve_resolves_callables_returning_callables() -> None:
    assert resolve(lambda page: lambda page: page + "!", page="hi") == "hi!"
