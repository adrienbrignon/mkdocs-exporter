import importlib.metadata
import importlib.util
import logging
import posixpath
from functools import cache
from pathlib import Path
from types import ModuleType

import mkdocs_exporter

EXAMPLES = Path(__file__).parent.parent / "examples"
"""The example projects (see `examples/build.py`)."""

PUBLISHED = "assets/examples"
"""Where the documents of the examples are published, in the website."""

LANGUAGES = {".css": "css", ".j2": "html+jinja", ".md": "markdown", ".yml": "yaml"}
"""The language of code blocks, by file extension."""

logger = logging.getLogger("mkdocs.macros.examples")


@cache
def examples() -> ModuleType:
    """The module building the examples (`examples/build.py`)."""

    spec = importlib.util.spec_from_file_location("examples", EXAMPLES / "build.py")

    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load {EXAMPLES / 'build.py'}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module


def define_env(env):
    """
    A hook for the MkDocs Macros plugin.
    """

    env.variables["version"] = importlib.metadata.version(mkdocs_exporter.__name__)

    @env.macro
    def example(path: str, indent: int = 4) -> str:
        """A file of an example project, as a code block.

        Lines after the first one are indented (by `indent` spaces), so that the block
        can be placed in tabs or admonitions. The `INHERIT` key of configuration files
        (the settings shared by the example projects) is left out.
        """

        file = EXAMPLES / path
        lines = [
            line
            for line in file.read_text(encoding="utf-8").splitlines()
            if not line.startswith("INHERIT:")
        ]

        while lines and not lines[0].strip():
            lines.pop(0)

        block = [f"``` {LANGUAGES.get(file.suffix, '')}", *lines, "```"]

        return ("\n" + " " * indent).join(block)

    @env.macro
    def previews(*items: str, indent: int = 0) -> str:
        """Previews of the documents of examples, each opening its document at its page.

        Items are sites (every preview of a site) or `site:n` (its n-th preview), see
        `PREVIEWS` in `examples/build.py`. Links to the documents follow the previews.
        """

        page = env.page
        root = posixpath.relpath(".", posixpath.dirname(page.url) or ".")
        here = posixpath.dirname(page.file.src_uri)
        images, links = [], {}

        for item in items:
            site, _, only = item.partition(":")

            for index, (document, number, caption) in enumerate(
                examples().PREVIEWS[site], 1
            ):
                if only and index != int(only):
                    continue

                url = f"{root}/{PUBLISHED}/{site}/{document}"
                image = posixpath.relpath(
                    f"assets/images/examples/{site}-{index}.webp", here
                )
                anchor = f"#page={number}" if number > 0 else ""

                images.append(
                    f'<a href="{url}{anchor}" title="Open the document at this page">'
                    f"![{caption}]({image})</a>"
                )
                links.setdefault(url, (site, document))

        names = [document for _, document in links.values()]
        buttons = [
            f'<a class="md-button" href="{url}">:material-file-pdf-box: '
            f"{document}{f' ({site})' if names.count(document) > 1 else ''}</a>"
            for url, (site, document) in links.items()
        ]
        lines = [
            '<div class="previews" markdown>',
            "",
            *images,
            "",
            "</div>",
            "",
            " ".join(buttons),
        ]

        return ("\n" + " " * indent).join(lines)


def on_post_build(env):
    """Publishes the documents of the examples with the website.

    The examples are built when the plugin generates documents (not while serving, nor
    with `MKDOCS_EXPORTER_PDF=false`).
    """

    exporter = env.conf.plugins.get("exporter")

    if exporter is None or not exporter.pdf:
        return

    logger.info("Building the examples...")
    examples().publish(Path(env.conf.site_dir) / PUBLISHED)
