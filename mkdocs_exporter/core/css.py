from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import tinycss2
from tinycss2 import ast
from tinycss2.ast import Node
from tinycss2.serializer import serialize_string_value, serialize_url

from mkdocs_exporter.logging import logger

UNSCOPABLE = frozenset(
    {
        "counter-style",
        "font-face",
        "font-feature-values",
        "import",
        "keyframes",
        "page",
        "property",
    }
)
"""At-rules that can't be nested in `@scope` (they stay global)."""

PIXELS = {
    "px": 1.0,
    "cm": 96 / 2.54,
    "mm": 96 / 25.4,
    "q": 96 / 101.6,
    "in": 96.0,
    "pt": 96 / 72,
    "pc": 16.0,
}
"""CSS pixels per absolute unit."""


def string(text: str) -> str:
    """A CSS string holding a text (e.g. the `content` of a margin box)."""

    return f'"{serialize_string_value(text)}"'


def pixels(length: str) -> float | None:
    """A length in pixels (`None` for relative lengths and keywords)."""

    token = tinycss2.parse_one_component_value(length)

    if isinstance(token, ast.NumberToken):
        return float(token.value)
    if isinstance(token, ast.DimensionToken) and token.lower_unit in PIXELS:
        return float(token.value) * PIXELS[token.lower_unit]

    return None


@dataclass(frozen=True)
class PageSelector:
    """A selector of `@page` rules: a page name and pseudo-classes (`:first`...)."""

    name: str | None = None
    pseudos: tuple[str, ...] = ()

    def __str__(self) -> str:
        return (self.name or "") + "".join(f":{pseudo}" for pseudo in self.pseudos)

    def matches(self, name: str | None, first: bool, right: bool) -> bool:
        """Does it select a page (of a name, the first one, a right page)?"""

        return not (
            (self.name and self.name != name)
            or ("first" in self.pseudos and not first)
            or "blank" in self.pseudos
            or ("left" in self.pseudos and right)
            or ("right" in self.pseudos and not right)
        )

    @property
    def specificity(self) -> tuple[int, int, int]:
        """Its specificity: page name, then `:first`, then `:left` / `:right`."""

        return (
            int(self.name is not None),
            self.pseudos.count("first"),
            self.pseudos.count("left") + self.pseudos.count("right"),
        )

    @classmethod
    def parse(cls, selector: str) -> PageSelector | None:
        """Parses a selector (`None` when it isn't a valid page selector)."""

        tokens = [
            token
            for token in tinycss2.parse_component_value_list(selector)
            if token.type not in ("whitespace", "comment")
        ]
        name = None

        if tokens and isinstance(tokens[0], ast.IdentToken):
            name = tokens.pop(0).value

        pseudos = []

        for colon, ident in zip(tokens[::2], tokens[1::2], strict=False):
            if not (_literal(colon, ":") and isinstance(ident, ast.IdentToken)):
                return None

            pseudos.append(ident.lower_value)

        if len(tokens) % 2:
            return None

        return cls(name, tuple(pseudos))


def selector_list(selector: str | Sequence[Node]) -> list[str]:
    """The selectors of a selector list (e.g. the prelude of a rule)."""

    tokens = (
        tinycss2.parse_component_value_list(selector)
        if isinstance(selector, str)
        else selector
    )
    selectors: list[list[Node]] = [[]]

    for token in tokens:
        if _literal(token, ","):
            selectors.append([])
        else:
            selectors[-1].append(token)

    return [tinycss2.serialize(tokens).strip() for tokens in selectors]


@dataclass(frozen=True)
class PageMargin:
    """The top margin set by a `@page` rule."""

    selector: str
    top: str


def top_margin(
    rules: Sequence[PageMargin], name: str | None, first: bool, right: bool
) -> float:
    """The top margin (in pixels) of a page, from the `@page` rules setting one.

    Rules apply by specificity, then in order, as defined by CSS Paged Media.
    """

    best: tuple[tuple[int, int, int], int] | None = None
    margin = 0.0

    for order, rule in enumerate(rules):
        value = pixels(rule.top)

        if value is None:
            continue

        for text in selector_list(rule.selector):
            selector = PageSelector.parse(text)

            if selector is None or not selector.matches(name, first, right):
                continue
            if best is None or (selector.specificity, order) >= best:
                best = (selector.specificity, order)
                margin = value

    return margin


def rewrite_urls(css: str, rewrite: Callable[[str], str]) -> str:
    """Rewrites the URLs (`url()`) of a stylesheet or of declarations (`style`)."""

    changes = _Changes(rewrite)

    def visit(token: Node) -> Node:
        url = _url(token)

        return token if url is None else _url_token(token, changes(url))

    tokens = _map(tinycss2.parse_component_value_list(css), visit)

    return tinycss2.serialize(tokens) if changes.made else css


def rename_selector_ids(selector: str, rename: Callable[[str], str]) -> str:
    """Renames the identifiers of a selector (`#id`)."""

    changes = _Changes(rename)
    tokens = _map(tinycss2.parse_component_value_list(selector), _hash_renamer(changes))

    return tinycss2.serialize(tokens) if changes.made else selector


def rewrite_ids(css: str, rename: Callable[[str], str]) -> str:
    """Renames the identifiers of a stylesheet's selectors (`#id`) and of `url(#id)`.

    Hashes of values (e.g. colors) are left untouched.
    """

    rename = changes = _Changes(rename)

    def references(tokens: list[Node]) -> list[Node]:
        def visit(token: Node) -> Node:
            url = _url(token)

            if url is not None and url.startswith("#"):
                return _url_token(token, "#" + rename(url[1:]))

            return token

        return _map(tokens, visit)

    def selectors(tokens: list[Node]) -> list[Node]:
        return _map(tokens, _hash_renamer(rename))

    def rules(nodes: list[Node]) -> list[Node]:
        for node in nodes:
            if isinstance(node, ast.QualifiedRule):
                node.prelude = selectors(node.prelude)
            elif isinstance(node, ast.AtRule):
                node.prelude = references(node.prelude)
            elif isinstance(node, ast.Declaration):
                node.value = references(node.value)
            # Blocks holding invalid CSS keep their content, but their references.
            if (
                isinstance(node, (ast.QualifiedRule, ast.AtRule))
                and node.content
                and not _rewrite_block(node, rules)
            ):
                node.content = references(node.content)

        return nodes

    try:
        nodes = rules(_stylesheet(css))
    except InvalidStylesheet:
        return css

    return tinycss2.serialize(nodes) if changes.made else css


@dataclass(frozen=True)
class PageRule:
    """A `@page` rule."""

    selectors: list[str]
    """Its selectors (an empty one for a rule without selector)."""

    block: str
    """Its block (`{...}`)."""


def split_page_rules(css: str) -> tuple[list[PageRule], str]:
    """Takes the `@page` rules out of a stylesheet (at any depth: those of `@media`...).

    Returns:
        The `@page` rules, and the rest of the stylesheet.
    """

    rules: list[PageRule] = []

    def walk(nodes: list[Node]) -> list[Node]:
        kept = []

        for node in nodes:
            if isinstance(node, ast.AtRule) and node.lower_at_keyword == "page":
                block = "{" + tinycss2.serialize(node.content or []) + "}"
                rules.append(PageRule(selector_list(node.prelude), block))
                continue
            if isinstance(node, (ast.AtRule, ast.QualifiedRule)) and node.content:
                _rewrite_block(node, walk)

            kept.append(node)

        return kept

    try:
        nodes = walk(_stylesheet(css))
    except InvalidStylesheet:
        return [], css

    return rules, tinycss2.serialize(nodes) if rules else css


def rename_pages(css: str, names: Mapping[str, str]) -> str:
    """Renames the pages named by `page` properties."""

    renamed = False

    def walk(nodes: list[Node]) -> list[Node]:
        for node in nodes:
            if isinstance(node, ast.Declaration) and node.lower_name == "page":
                nonlocal renamed
                renamed |= any(
                    isinstance(t, ast.IdentToken) and t.value in names
                    for t in node.value
                )
                node.value = [
                    ast.IdentToken(t.source_line, t.source_column, names[t.value])
                    if isinstance(t, ast.IdentToken) and t.value in names
                    else t
                    for t in node.value
                ]
            elif isinstance(node, (ast.AtRule, ast.QualifiedRule)) and node.content:
                _rewrite_block(node, walk)

        return nodes

    try:
        nodes = walk(_stylesheet(css))
    except InvalidStylesheet:
        return css

    return tinycss2.serialize(nodes) if renamed else css


def scope(css: str, selector: str) -> str:
    """Scopes the rules of a stylesheet to the elements matching a selector (`@scope`).

    At-rules that can't be scoped (`@font-face`, `@keyframes`...) stay global.
    """

    outside: list[Node] = []
    inside: list[Node] = []

    try:
        nodes = _stylesheet(css)
    except InvalidStylesheet:
        return f"@scope ({selector}) {{\n{css}\n}}"

    for node in nodes:
        unscopable = (
            isinstance(node, ast.AtRule) and node.lower_at_keyword in UNSCOPABLE
        )
        (outside if unscopable else inside).append(node)

    scoped = tinycss2.serialize(inside).strip()
    result = tinycss2.serialize(outside).strip()

    if scoped:
        result += f"\n@scope ({selector}) {{\n{scoped}\n}}"

    return result.strip()


class _Changes:
    """Calls a function, telling whether it ever returned something else than its
    argument (stylesheets left unchanged are not serialized again)."""

    def __init__(self, function: Callable[[str], str]) -> None:
        self.function = function
        self.made = False

    def __call__(self, value: str) -> str:
        result = self.function(value)
        self.made |= result != value

        return result


class InvalidStylesheet(ValueError):
    """A stylesheet that can't be parsed (it is then left as it is)."""


def _stylesheet(css: str | list[Node]) -> list[Node]:
    """The rules of a stylesheet (`InvalidStylesheet` if one of them is invalid)."""

    nodes = tinycss2.parse_stylesheet(css, skip_comments=False, skip_whitespace=False)

    if any(node.type == "error" for node in nodes):
        logger.debug("[mkdocs-exporter.pdf] Invalid CSS left as it is: %.80r", css)

        raise InvalidStylesheet(css)

    return nodes


def _rewrite_block(node: Node, rewrite: Callable[[list[Node]], list[Node]]) -> bool:
    """Rewrites the declarations and rules of a block, unless one of them is invalid.

    Returns:
        Was the block rewritten?
    """

    contents = _contents(node.content)

    if contents is None:
        return False

    node.content = _tokens(rewrite(contents))

    return True


def _contents(tokens: list[Node]) -> list[Node] | None:
    """The declarations and rules of a block (nested rules included), `None` when one
    of them is invalid.

    The whitespace ending declarations is moved after them, so that the semicolons
    added when they are serialized follow their value.
    """

    nodes = []

    for node in tinycss2.parse_blocks_contents(
        tokens, skip_comments=False, skip_whitespace=False
    ):
        if node.type == "error":
            return None

        nodes.append(node)

        if isinstance(node, ast.Declaration):
            index = len(node.value)

            while index and node.value[index - 1].type == "whitespace":
                index -= 1

            nodes += node.value[index:]
            node.value = node.value[:index]

    return nodes


def _tokens(nodes: list[Node]) -> list[Node]:
    """Nodes, as the tokens of a block's content."""

    return tinycss2.parse_component_value_list(tinycss2.serialize(nodes))


def _literal(token: Node, value: str) -> bool:
    return isinstance(token, ast.LiteralToken) and token.value == value


def _hash_renamer(rename: Callable[[str], str]) -> Callable[[Node], Node]:
    def visit(token: Node) -> Node:
        if isinstance(token, ast.HashToken) and token.is_identifier:
            value = rename(token.value)

            return ast.HashToken(token.source_line, token.source_column, value, True)

        return token

    return visit


def _map(tokens: list[Node], visit: Callable[[Node], Node]) -> list[Node]:
    result = []

    for token in tokens:
        if isinstance(
            token,
            (ast.ParenthesesBlock, ast.SquareBracketsBlock, ast.CurlyBracketsBlock),
        ):
            token.content = _map(token.content, visit)
        elif isinstance(token, ast.FunctionBlock) and token.lower_name != "url":
            token.arguments = _map(token.arguments, visit)

        result.append(visit(token))

    return result


def _url(token: Node) -> str | None:
    if isinstance(token, ast.URLToken):
        return token.value
    if isinstance(token, ast.FunctionBlock) and token.lower_name == "url":
        strings = [t for t in token.arguments if isinstance(t, ast.StringToken)]

        return strings[0].value if strings else None

    return None


def _url_token(token: Node, url: str) -> Node:
    """A `url()` leading to another URL, quoted like the original one."""

    if isinstance(token, ast.URLToken):
        representation = f"url({serialize_url(url)})"
    else:
        representation = f'url("{serialize_string_value(url)}")'

    return ast.URLToken(token.source_line, token.source_column, url, representation)
