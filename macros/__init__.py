import importlib.metadata
from pathlib import Path

import mkdocs_exporter

EXAMPLES = Path(__file__).parent.parent / "examples"
"""The example projects (see `examples/build.py`)."""

LANGUAGES = {".css": "css", ".j2": "html+jinja", ".md": "markdown", ".yml": "yaml"}
"""The language of code blocks, by file extension."""


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
