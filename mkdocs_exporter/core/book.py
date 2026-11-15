"""Combined documents ("books"): every page in a single HTML document, printed once.

A book is the first page's shell (head, scripts, hidden chrome) whose content element is
replaced by one *part* per page, in order. A part is the page's own content element
(e.g. Material's `article.md-content__inner`, attributes included, so that child
selectors such as `.md-content__inner > pre` still match) holding its kept covers.

Since every page lives in the same document:

- relative URLs are resolved against the page they come from (`rewrite_urls`), links to
  other parts become anchors within the book, other links lead to the website;
- identifiers (and every reference to them) are prefixed by part, as well as the names of
  radio groups (tabs), so that parts don't interfere with each other (`namespace_ids`);
- stylesheets and scripts loaded by some pages only are merged into the shell;
- styles teleported to the head (e.g. by cover templates) are translated: `@page :first`
  becomes the covers' named page, and styles that differ between pages are scoped to their
  part (`part_styles`);
- named pages give covers, the table of contents and blank pages their own margin boxes,
  and each part its own `{page_title}` (`structure`).
"""

from __future__ import annotations

import copy
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup, Tag

from mkdocs_exporter.core import margins
from mkdocs_exporter.core.document import Document
from mkdocs_exporter.core.html import ANCESTOR, HtmlDocument, resolve_link

FRONT_COVER_PAGE = "mkdocs-exporter-front-cover"
"""The named page of front covers."""

BACK_COVER_PAGE = "mkdocs-exporter-cover"
"""The named page of back covers (the same as in single documents)."""

CONTENT_PAGE = "mkdocs-exporter-content"
"""The named page of the parts' content, when they don't need one of their own."""

TOC_PAGE = "mkdocs-exporter-toc"
"""The named page of the table of contents."""

BLANK_PAGE = "mkdocs-exporter-blank"
"""The named page of blank pages (see `start: odd`)."""

ORIGIN = "http://mkdocs-exporter.invalid"
"""A placeholder origin to resolve URLs with."""

PLACEHOLDER = "<!--mkdocs-exporter-parts-->"
"""Where the parts are inserted in the serialized shell."""

HEADINGS = ("h1", "h2", "h3", "h4", "h5", "h6")
EXCLUDED = ("mkdocs-exporter-front-cover", "mkdocs-exporter-back-cover")

ID_ATTRIBUTES = ("for", "form", "list")
"""Attributes holding an identifier."""

ID_LIST_ATTRIBUTES = (
    "headers",
    "aria-activedescendant",
    "aria-controls",
    "aria-describedby",
    "aria-details",
    "aria-errormessage",
    "aria-flowto",
    "aria-labelledby",
    "aria-owns",
)
"""Attributes holding a space-separated list of identifiers."""

URL_REFERENCES = (
    "clip-path",
    "fill",
    "filter",
    "marker-end",
    "marker-mid",
    "marker-start",
    "mask",
    "stroke",
    "style",
)
"""Attributes that may reference an element with `url(#id)` (SVG, styles)."""

RESOURCES = {
    "src": (
        "audio",
        "embed",
        "iframe",
        "img",
        "input",
        "script",
        "source",
        "track",
        "video",
    ),
    "poster": ("video",),
    "data": ("object",),
    "action": ("form",),
}
"""Attributes holding the URL of a resource, by element."""

HYPERLINKS = ("a", "area")
"""Elements whose `href` is a link (the `href` of other elements is a resource)."""

CSS_URL = re.compile(r"""url\(\s*(['"]?)([^'")]*)\1\s*\)""")
CSS_ID = re.compile(r"#([^\W\d][\w-]*)")
PAGE_RULE = re.compile(r"@page\b([^{;]*)\{")
PAGE_PROPERTY = re.compile(r"(?<![\w-])page\s*:\s*([A-Za-z_][\w-]*)")
UNSCOPABLE = re.compile(
    r"@(?:font-face|keyframes|counter-style|property|font-feature-values|import)\b"
)


@dataclass
class Part:
    """A page, as a part of a book."""

    index: int
    document: Document
    covers: set[str]
    """The covers kept."""

    html: HtmlDocument | None
    """The page, as parsed (the shell of the book, for the first part); `None` when the
    part reuses the content prepared for the page's own document (see `Prepared`)."""

    content: Tag
    """The page's content element (the part's element)."""

    resources: PageResources | None = None
    """The stylesheets and scripts of the page (read from `html` when missing)."""

    prepared: bool = False
    """Was the content already prepared for printing (covers, title...)?"""

    ids: set[str] = field(default_factory=set)
    """The identifiers defined by the part (before being namespaced)."""

    headings: list[tuple[int, str, str]] = field(default_factory=list)
    """Its headings (level, namespaced identifier, title), outside of covers."""

    styles: list[str] = field(default_factory=list)
    """The styles it teleports to the head (e.g. its covers')."""

    teleported: list[Tag] = field(default_factory=list)
    """The other elements it teleports (to the shell)."""

    @property
    def id(self) -> str:
        """The identifier of the part's element."""

        return f"mkdocs-exporter-part-{self.index}"

    @property
    def prefix(self) -> str:
        """The prefix of the part's identifiers."""

        return f"p{self.index}-"

    @property
    def anchor(self) -> str:
        """Where links to the part lead: its first heading, or the part itself."""

        return self.headings[0][1] if self.headings else self.id


@dataclass
class BookOptions:
    """How pages are turned into a book."""

    prefix: str = "/"
    """The path under which the website is served (e.g. `/docs/`)."""

    links: str = "/"
    """The URL replacing the website's root in links to pages that aren't parts."""

    removed: Sequence[str] = ()
    """Selectors of elements removed from pages before printing."""

    hidden: Sequence[str] = ()
    """Selectors of elements hidden in the book."""

    head: Sequence[str] = ()
    """HTML inserted at the start of the head, in order (scripts that must run first)."""

    base_stylesheets: Sequence[str] = ()
    """Stylesheets of the exporter and the theme (before headers and footers)."""

    stylesheets: Sequence[str] = ()
    """Stylesheets of the user (after headers and footers, before teleported styles)."""

    scripts: Sequence[str] = ()
    """Scripts appended to the body."""

    margins: Mapping[str, Mapping[str, str | None]] = field(default_factory=dict)
    """Headers and footers (see `mkdocs_exporter.core.margins`)."""

    variables: Mapping[str, str] = field(default_factory=dict)
    """Values of the placeholders of headers and footers (e.g. `site_name`)."""

    toc_title: str = ""
    """The `{page_title}` of the pages of the table of contents."""


@dataclass
class Book:
    """An HTML document combining pages."""

    html: str
    parts: list[Part]
    pages: PageNames


@dataclass
class PageNames:
    """The named pages of a book's parts, by part identifier."""

    first: dict[str, str] = field(default_factory=dict)
    """The name of the first page of each part (its front cover's, its content's...)."""

    front: dict[str, str] = field(default_factory=dict)
    """The name of the pages of front covers."""

    content: dict[str, str] = field(default_factory=dict)
    """The name of the pages of each part's content."""


# --- URLs ------------------------------------------------------------------------------


def is_relative(url: str) -> bool:
    """Is a URL relative to the page (neither absolute, nor an anchor, nor `data:`...)?"""

    url = url.strip()

    return bool(url) and not url.startswith(("#", "//")) and not urlsplit(url).scheme


def resource_url(url: str, page_url: str, prefix: str) -> str:
    """Resolves the URL of a resource found in a page as a root-absolute URL.

    `../img/logo.png` found in `guide/intro/` becomes `<prefix>guide/img/logo.png`. URLs
    that are already root-absolute are kept: the server resolves them against the
    website's prefix, then against its root.
    """

    if not is_relative(url) or url.startswith("/"):
        return url

    target = urlsplit(urljoin(ORIGIN + prefix + page_url, url.strip()))

    return urlunsplit(("", "", target.path, target.query, target.fragment))


def site_path(url: str, page_url: str, prefix: str) -> tuple[str, str] | None:
    """The path (relative to the website's root) and fragment a link leads to.

    `None` for anchors and links leaving the website. Root-absolute paths outside the
    prefix are relative to the website's root (like `resolve_link`).
    """

    if not is_relative(url):
        return None

    target = urlsplit(urljoin(ORIGIN + prefix + page_url, url.strip()))
    path = unquote(target.path)
    path = path[len(prefix) :] if path.startswith(prefix) else path.lstrip("/")

    if path.endswith("index.html"):
        path = path[: -len("index.html")]

    return path, unquote(target.fragment)


def _rewrite_css_urls(css: str, rewrite: Callable[[str], str]) -> str:
    return CSS_URL.sub(lambda m: f'url("{rewrite(m.group(2))}")', css)


def _rewrite_srcset(srcset: str, rewrite: Callable[[str], str]) -> str:
    candidates = []

    for candidate in srcset.split(","):
        url, _, descriptor = candidate.strip().partition(" ")
        candidates.append(f"{rewrite(url)} {descriptor}".strip())

    return ", ".join(candidates)


def rewrite_urls(
    element: Tag,
    page_url: str,
    prefix: str,
    link: Callable[[str, str], str | None],
    base: str | None = None,
) -> None:
    """Makes the URLs found in an element valid wherever the element is served.

    Resources (`src`, `srcset`, `poster`, `data`, `action`, the `href` of `<link>`, SVG
    `href` and `xlink:href`, `url()` of `style` attributes and `<style>` elements) become
    root-absolute. Links (`<a>`, `<area>`) are given to `link` with the path (relative to
    the website's root) and fragment they lead to; it returns their new target (`None`
    keeps them as they are). Links starting with `base` (already resolved, see
    `resolve_link`) lead to the website's root followed by the rest of their URL.
    """

    def resource(url: str) -> str:
        return resource_url(url, page_url, prefix)

    for attribute, names in RESOURCES.items():
        for tag in element.find_all(names, attrs={attribute: True}):
            tag[attribute] = resource(str(tag[attribute]))
    for tag in element.find_all(["img", "source"], attrs={"srcset": True}):
        tag["srcset"] = _rewrite_srcset(str(tag["srcset"]), resource)
    for tag in element.find_all(True, attrs={"style": True}):
        if "url(" in str(tag["style"]):
            tag["style"] = _rewrite_css_urls(str(tag["style"]), resource)
    for tag in element.find_all("style"):
        if tag.string and "url(" in tag.string:
            tag.string = _rewrite_css_urls(tag.string, resource)
    for tag in element.find_all(True, attrs={"href": True}):
        href = str(tag["href"])

        if base and href.startswith(base):
            href = prefix + href[len(base) :]
        if tag.name not in HYPERLINKS:
            tag["href"] = resource(href)
        elif (target := site_path(href, page_url, prefix)) is not None and (
            rewritten := link(*target)
        ) is not None:
            tag["href"] = rewritten
    for tag in element.find_all(True, attrs={"xlink:href": True}):
        tag["xlink:href"] = resource(str(tag["xlink:href"]))


# --- Identifiers -----------------------------------------------------------------------


def collect_ids(element: Tag) -> set[str]:
    """The identifiers (and names of anchors and image maps) defined within an element."""

    ids = {str(tag["id"]) for tag in element.find_all(True, attrs={"id": True})}
    ids |= {
        str(tag["name"]) for tag in element.find_all(["a", "map"], attrs={"name": True})
    }

    return ids


def namespace_ids(element: Tag, prefix: str, ids: set[str]) -> None:
    """Prefixes the identifiers defined within an element, and every reference to them.

    Rewritten: `id`; the `name` of anchors, image maps and radio buttons (radio groups
    span the whole document: tabs of different parts sharing a group would uncheck each
    other); anchors in `href` and `xlink:href`; `for`, `form`, `list`, `headers`, `usemap`
    and ARIA references; `url(#id)` of SVG attributes, `style` attributes and `<style>`
    elements; `#id` selectors of `<style>` elements and `data-clipboard-target`.
    """

    def reference(value: str) -> str:
        return prefix + value if value in ids else value

    def anchor(href: str) -> str:
        if href.startswith("#") and unquote(href[1:]) in ids:
            return "#" + prefix + href[1:]

        return href

    def urls(text: str) -> str:
        return CSS_URL.sub(
            lambda m: f"url({m.group(1)}{anchor(m.group(2))}{m.group(1)})", text
        )

    def selectors(text: str) -> str:
        return CSS_ID.sub(lambda m: "#" + reference(m.group(1)), text)

    for tag in element.find_all(True):
        attrs = tag.attrs

        if "id" in attrs:
            attrs["id"] = prefix + str(attrs["id"])
        if "name" in attrs and (
            tag.name in ("a", "map")
            or (tag.name == "input" and str(attrs.get("type", "")).lower() == "radio")
        ):
            attrs["name"] = prefix + str(attrs["name"])

        for key in ("href", "xlink:href", "usemap"):
            if key in attrs:
                attrs[key] = anchor(str(attrs[key]))
        for key in ID_ATTRIBUTES:
            if isinstance(value := attrs.get(key), str):
                attrs[key] = reference(value)
        for key in ID_LIST_ATTRIBUTES:
            if key in attrs:
                value = attrs[key]
                tokens = value if isinstance(value, list) else str(value).split()
                attrs[key] = " ".join(reference(token) for token in tokens)
        for key in URL_REFERENCES:
            if key in attrs and "url(" in str(attrs[key]):
                attrs[key] = urls(str(attrs[key]))

        if "data-clipboard-target" in attrs:
            attrs["data-clipboard-target"] = selectors(
                str(attrs["data-clipboard-target"])
            )
        if tag.name == "style" and tag.string:
            tag.string = selectors(urls(tag.string))


# --- Styles ----------------------------------------------------------------------------


def _block_end(css: str, start: int) -> int:
    """The index following the `}` closing the block opened at `start` (a `{`)."""

    depth = 0
    index = start
    quote = None

    while index < len(css):
        char = css[index]

        if quote:
            if char == "\\":
                index += 1
            elif char == quote:
                quote = None
        elif css.startswith("/*", index):
            end = css.find("*/", index + 2)
            index = len(css) if end < 0 else end + 1
        elif char in "\"'":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1

            if depth == 0:
                return index + 1

        index += 1

    return len(css)


def page_rules(css: str) -> list[tuple[int, int, str]]:
    """The `@page` rules of a stylesheet, at any depth: (start, end, selector)."""

    rules = []
    position = 0

    while match := PAGE_RULE.search(css, position):
        end = _block_end(css, match.end() - 1)
        rules.append((match.start(), end, match.group(1).strip()))
        position = end

    return rules


def translate_selector(
    selector: str, first: Sequence[str], every: Sequence[str], names: Mapping[str, str]
) -> list[str]:
    """Translates the selector of a `@page` rule written for a document of its own.

    Args:
        selector: The selector (e.g. `:first`, `cover:left`).
        first: The named pages `:first` stands for.
        every: The named pages a rule without page name applies to (none: unchanged).
        names: Page names to rename.

    Returns:
        The selectors of the rules to write (one per named page).
    """

    translated = []

    for item in selector.split(","):
        item = item.strip()
        match = re.fullmatch(r"([A-Za-z_][\w-]*)?((?::[\w-]+)*)", item)

        if match is None:
            translated.append(item)
            continue

        name, pseudos = match.group(1), match.group(2)

        if name:
            translated.append(names.get(name, name) + pseudos)
        elif ":first" in pseudos:
            translated += [page + pseudos.replace(":first", "") for page in first]
        elif every:
            translated += [page + pseudos for page in every]
        else:
            translated.append(item)

    return translated


def translate_page_rules(
    css: str,
    first: Sequence[str],
    every: Sequence[str] = (),
    names: Mapping[str, str] | None = None,
) -> tuple[str, str]:
    """Translates the `@page` rules of a stylesheet (see `translate_selector`).

    Chromium's `:first` only matches the first page of the whole book, and doesn't
    support selector lists: each rule is written once per selector.

    Returns:
        The translated `@page` rules, and the rest of the stylesheet (with the `page`
        properties renamed according to `names`).
    """

    names = names or {}
    pages = []
    rest = []
    position = 0

    for start, end, selector in page_rules(css):
        body = css[css.index("{", start) : end]

        for translated in translate_selector(selector, first, every, names):
            pages.append(f"@page {translated} {body}")

        rest.append(css[position:start])
        position = end

    rest.append(css[position:])
    remainder = "".join(rest)

    if names:
        remainder = PAGE_PROPERTY.sub(
            lambda m: f"page: {names.get(m.group(1), m.group(1))}", remainder
        )

    return "\n".join(pages), remainder


def scope_styles(css: str, scope: str) -> str:
    """Scopes the rules of a stylesheet to the elements matching a selector (`@scope`).

    At-rules that can't be scoped (`@font-face`, `@keyframes`...) stay global.
    """

    outside = []
    inside = []
    position = 0

    while match := UNSCOPABLE.search(css, position):
        brace = css.find("{", match.end())
        semicolon = css.find(";", match.end())

        if brace < 0 or 0 <= semicolon < brace:
            end = semicolon + 1 if semicolon >= 0 else len(css)
        else:
            end = _block_end(css, brace)

        inside.append(css[position : match.start()])
        outside.append(css[match.start() : end])
        position = end

    inside.append(css[position:])
    scoped = "".join(inside).strip()

    if scoped:
        outside.append(f"@scope ({scope}) {{\n{scoped}\n}}")

    return "\n".join(outside)


def part_styles(parts: Sequence[Part]) -> tuple[list[str], PageNames]:
    """Translates the styles teleported to the head by the parts, and names their pages.

    Styles identical for every part teleporting some (the usual case: cover templates
    only use the website's variables in their styles) are included once, every front
    cover being on the `mkdocs-exporter-front-cover` page. Otherwise, every part gets
    pages of its own (`mkdocs-exporter-front-cover-N`, `mkdocs-exporter-part-N`), its
    `@page` rules are translated to them and its other rules scoped to the part.

    Returns:
        The stylesheets, and the names of the parts' pages (front covers and content;
        contents without a page of their own are left out).
    """

    names = PageNames()
    styled = [part for part in parts if part.styles]
    variants = {tuple(part.styles) for part in styled}

    if len(variants) <= 1:
        for part in parts:
            names.front[part.id] = FRONT_COVER_PAGE

        return [
            "\n".join(reversed(translate_page_rules(css, [FRONT_COVER_PAGE])))
            for css in next(iter(variants), ())
        ], names

    styles = []

    for part in parts:
        front = f"{FRONT_COVER_PAGE}-{part.index}"
        content = f"mkdocs-exporter-part-{part.index}"
        names.front[part.id] = front
        names.content[part.id] = content

        for css in part.styles:
            defined = {
                name
                for _, _, selector in page_rules(css)
                for name in re.findall(r"(?:^|,)\s*([A-Za-z_][\w-]*)", selector)
            }
            pages, rest = translate_page_rules(
                css,
                [front],
                [content, front],
                {name: f"{name}-{part.index}" for name in defined},
            )
            styles.append(scope_styles(rest, f"#{part.id}") + "\n" + pages)

    return styles, names


def first_pages(css: str, parts: Sequence[Part], names: PageNames) -> str:
    """Translates the `@page :first` rules of a stylesheet applied to every page.

    In a page's own document, the first page is its front cover: in a book, `:first`
    would only match the book's first page. These rules apply to the pages of front
    covers instead (or to the book's first page when no part has a front cover).
    """

    covers = sorted({names.front[p.id] for p in parts if "front" in p.covers})

    if not covers or ":first" not in css:
        return css

    pages, rest = translate_page_rules(css, covers)

    return rest + "\n" + pages


def structure(
    parts: Sequence[Part],
    names: PageNames,
    toc: bool,
    titled: bool = False,
    back_covers: bool = False,
) -> str:
    """The stylesheet laying parts out on their pages.

    Each part starts on a new page; covers, the table of contents and blank pages are on
    named pages, as well as each part's content when headers or footers show its title
    (`titled`), and back covers when headers or footers are hidden there (`back_covers`,
    like in single documents). A change of named page starts a new page, even for an
    empty box: `body`
    and each part are given the name of their first page, and parts lose their
    pseudo-elements (e.g. Material's spacer), so that no page holds only empty boxes.
    """

    rules = [
        ".mkdocs-exporter-part + .mkdocs-exporter-part,"
        " .mkdocs-exporter-blank + .mkdocs-exporter-part { break-before: page; }",
        ".mkdocs-exporter-part::before, .mkdocs-exporter-part::after"
        " { content: none !important; }",
        f".mkdocs-exporter-blank {{ page: {BLANK_PAGE}; break-before: page;"
        " break-after: page; }",
        f".mkdocs-exporter-toc {{ page: {TOC_PAGE}; }}",
    ]

    for part in parts:
        front = names.front.get(part.id, FRONT_COVER_PAGE)
        content = names.content.get(
            part.id, f"mkdocs-exporter-part-{part.index}" if titled else CONTENT_PAGE
        )
        first = content

        if "front" in part.covers:
            first = front
        elif toc and part.index == 0:
            first = TOC_PAGE

        names.first[part.id] = first
        names.content.setdefault(part.id, content)
        names.front.setdefault(part.id, front)
        rules += [
            f"#{part.id} {{ page: {first}; }}",
            f":where(#{part.id}) > * {{ page: {content}; }}",
            f"#{part.id} > .mkdocs-exporter-front-cover {{ page: {front}; }}",
        ]

    if back_covers:
        rules.append(
            f".mkdocs-exporter-part > .mkdocs-exporter-back-cover"
            f" {{ page: {BACK_COVER_PAGE}; }}"
        )
    if parts:
        rules.append(f"body {{ page: {names.first[parts[0].id]}; }}")

    return "\n".join(rules) + "\n"


# --- Assembly --------------------------------------------------------------------------


@dataclass
class Prepared:
    """A page's content prepared for its own document, reused as a part of books.

    It spares books another parse of the page: the content is detached from the page's
    document once that document is printed, links resolved (see `rewrite_urls`'s
    `base`) and every cover inserted.
    """

    content: Tag
    resources: PageResources
    teleported: list[tuple[str, str, Tag]] = field(default_factory=list)
    """The elements the content teleports: (origin, destination, element), the origin
    being the location of the cover holding the element (`front`, `back`) or `content`."""


def teleported(content: Tag) -> list[tuple[str, str, Tag]]:
    """The elements a page's content teleports (see `Prepared.teleported`)."""

    found = []

    for element in content.find_all(True, attrs={"data-teleport": True}):
        origin = "content"

        for location in ("front", "back"):
            cover = element.find_parent(class_=f"mkdocs-exporter-{location}-cover")

            if cover is not None and cover.parent is content:
                origin = location

        found.append((origin, str(element.get("data-teleport") or ""), element))

    return found


def reuse(index: int, document: Document, covers: set[str], prepared: Prepared) -> Part:
    """A part made of a page's prepared content, keeping only some of its covers."""

    part = Part(
        index=index,
        document=document,
        covers=covers,
        html=None,
        content=prepared.content,
        resources=prepared.resources,
        prepared=True,
    )

    for location in ("front", "back"):
        if location not in covers:
            for cover in prepared.content.find_all(
                class_=f"mkdocs-exporter-{location}-cover", recursive=False
            ):
                cover.decompose()

    for origin, destination, element in prepared.teleported:
        if origin != "content" and origin not in covers:
            continue
        if destination == "head" and element.name == "style":
            part.styles.append(element.string or "")
        else:
            element["data-teleport"] = destination
            part.teleported.append(element)

    return part


def within(tag: Tag, ancestor: Tag) -> bool:
    """Is a tag a descendant of another (by identity: `Tag.__eq__` compares markup)?"""

    return any(parent is ancestor for parent in tag.parents)


def headings(content: Tag) -> list[Tag]:
    """The headings of a part, outside of its covers (identifiers given if missing)."""

    covers = [
        tag
        for tag in content.find_all(class_=EXCLUDED)
        if isinstance(tag, Tag) and tag.parent is content
    ]
    found = []

    for index, tag in enumerate(content.find_all(HEADINGS)):
        if any(within(tag, cover) for cover in covers):
            continue
        if not tag.get("id"):
            tag["id"] = f"mkdocs-exporter-heading-{index}"

        found.append(tag)

    return found


def _title(tag: Tag) -> str:
    """The text of a heading."""

    return " ".join(tag.get_text().split())


def prepare(
    parts: Sequence[Part],
    options: BookOptions,
    prepare_content: Callable[[Part], None] = lambda part: None,
) -> None:
    """Prepares the parts' content: teleported elements, identifiers, URLs and headings.

    Args:
        parts: The parts, whose `content` holds their kept covers.
        options: The options of the book.
        prepare_content: Adjusts a part's content first (e.g. opens `<details>`).
    """

    by_url: dict[str, Part] = {}

    for part in parts:
        if not part.prepared:
            prepare_content(part)

        by_url.setdefault(part.document.url, part)

        for element in part.content.select("[data-teleport]"):
            destination = str(element.get("data-teleport") or "")

            if destination == "head" and element.name == "style":
                part.styles.append(element.string or "")
            else:
                part.teleported.append(element)

            element.extract()

        found = headings(part.content)
        part.ids = collect_ids(part.content)
        part.headings = [
            (int(tag.name[1]), part.prefix + str(tag["id"]), _title(tag))
            for tag in found
        ]

    for part in parts:

        def link(path: str, fragment: str, part: Part = part) -> str | None:
            target = by_url.get(path)

            if target is not None:
                if fragment and fragment in target.ids:
                    return "#" + target.prefix + fragment

                return "#" + target.anchor

            href = options.prefix + path + (f"#{fragment}" if fragment else "")

            return resolve_link(href, "", options.prefix, options.links)

        namespace_ids(part.content, part.prefix, part.ids)
        rewrite_urls(
            part.content, part.document.url, options.prefix, link, options.links
        )

        part.content["class"] = [  # type: ignore[assignment]
            *(part.content.get("class") or []),
            "mkdocs-exporter-part",
        ]
        part.content["id"] = part.id


@dataclass
class PageResources:
    """The stylesheets and scripts a page loads (outside of its content)."""

    stylesheets: list[str] = field(default_factory=list)
    """The (root-absolute) URLs of stylesheets."""

    styles: list[str] = field(default_factory=list)
    """The contents of `<style>` elements."""

    scripts: list[tuple[str, str]] = field(default_factory=list)
    """The scripts of the body: (key, HTML), the key identifying the script by URL,
    identifier or content."""


def page_resources(
    html: HtmlDocument, content: Tag, page_url: str, prefix: str, head: bool = False
) -> PageResources:
    """The stylesheets and scripts of a page, outside of its content.

    Scripts of the head are left out, unless `head` is set: they usually configure their
    own page.
    """

    resources = PageResources()
    document_head = html.soup.head

    for tag in html.soup.find_all(["link", "style", "script"]):
        if tag.name == "link":
            if tag.get("href") and "stylesheet" in (tag.get("rel") or []):
                href = resource_url(str(tag["href"]), page_url, prefix)
                resources.stylesheets.append(href)
            continue
        if within(tag, content):
            continue
        if tag.name == "style":
            if tag.string:
                resources.styles.append(tag.string)
            continue
        if not head and document_head is not None and within(tag, document_head):
            continue

        if tag.get("src"):
            tag = copy.copy(tag)
            tag["src"] = resource_url(str(tag["src"]), page_url, prefix)
            key = "src:" + str(tag["src"])
        elif tag.get("id"):
            key = "id:" + str(tag["id"])
        else:
            key = "text:" + (tag.string or "")

        resources.scripts.append((key, str(tag)))

    return resources


@dataclass
class _Resources:
    """The stylesheets and scripts loaded by the book so far."""

    stylesheets: set[str] = field(default_factory=set)
    styles: set[str] = field(default_factory=set)
    scripts: set[str] = field(default_factory=set)
    head: list[str] = field(default_factory=list)
    body: list[str] = field(default_factory=list)


def _merge(page: PageResources, resources: _Resources, shell: bool = False) -> None:
    """Merges the stylesheets and scripts of a page into the book's.

    Stylesheets are deduplicated by URL, styles by content, scripts by URL, identifier or
    content (a page may load a script others don't, e.g. a diagram library). Those of
    the shell (the first page) are only registered.
    """

    for href in page.stylesheets:
        if href not in resources.stylesheets and not shell:
            resources.head.append(f'<link rel="stylesheet" href="{href}">')

        resources.stylesheets.add(href)

    for text in page.styles:
        if text not in resources.styles and not shell:
            resources.head.append(f"<style>{text}</style>")

        resources.styles.add(text)

    for key, html in page.scripts:
        if key not in resources.scripts and not shell:
            resources.body.append(html)

        resources.scripts.add(key)


def assemble(parts: Sequence[Part], options: BookOptions, toc: str | None) -> Book:
    """Assembles prepared parts into a book (see `prepare`).

    Args:
        parts: The parts, in order (the first part's page is the shell).
        options: The options of the book.
        toc: The HTML of the table of contents, inserted after the first front cover.
    """

    first = parts[0]
    shell = first.html
    resources = _Resources()

    if shell is None:
        raise ValueError("The first part of a book must hold its page")

    for part in parts:
        page = part.resources

        if page is None and part.html is not None:
            page = page_resources(
                part.html,
                part.content,
                part.document.url,
                options.prefix,
                head=part is first,
            )

        _merge(page or PageResources(), resources, shell=part is first)

    if toc is not None:
        element = shell.fragment(toc, **{"class": "mkdocs-exporter-toc"})
        covers = first.content.find_all(
            class_="mkdocs-exporter-front-cover", recursive=False
        )

        if covers:
            covers[0].insert_after(element)
        else:
            first.content.insert(0, element)

    styles, names = part_styles(parts)
    titled = margins.uses(options.margins, "page_title")
    boxes = any(
        template is not None
        for positions in options.margins.values()
        for template in positions.values()
    )
    layout = structure(parts, names, toc is not None, titled, back_covers=boxes)
    titles = {
        names.content[part.id]: part.document.title
        for part in parts
        if titled and names.content[part.id] != CONTENT_PAGE
    }
    css = [
        *options.base_stylesheets,
        margins.book_stylesheet(
            options.margins,
            options.variables,
            {**titles, TOC_PAGE: options.toc_title},
            [*sorted(set(names.front.values())), BACK_COVER_PAGE],
            BLANK_PAGE,
        ),
        *(first_pages(css, parts, names) for css in options.stylesheets),
        layout,
    ]

    if options.hidden:
        css.append(", ".join(options.hidden) + " { display: none !important; }")

    # Teleported styles last, so that they take precedence (like in single documents).
    css += styles

    # Containers of the content are laid out as blocks in print (see `base.css`).
    shell.mark_ancestors(first.content, ANCESTOR)

    content = [str(part.content) for part in parts]
    first.content.replace_with(BeautifulSoup(PLACEHOLDER, "html.parser"))
    shell.remove(options.removed)

    head = shell.head
    head.append(BeautifulSoup("".join(resources.head), "html.parser"))

    for stylesheet in css:
        if stylesheet:
            shell.add_style(stylesheet)

    for element in (e for part in parts for e in part.teleported):
        selector = str(element.get("data-teleport") or "")
        destination = shell.select_one(selector) if selector else None

        if destination is not None:
            del element["data-teleport"]
            destination.append(element)

    for html in reversed(options.head):
        head.insert(0, BeautifulSoup(html, "html.parser"))

    body = shell.body
    body.append(BeautifulSoup("".join(resources.body), "html.parser"))

    for script in options.scripts:
        shell.add_script(script)

    return Book(
        html=str(shell).replace(PLACEHOLDER, "".join(content), 1),
        parts=list(parts),
        pages=names,
    )
