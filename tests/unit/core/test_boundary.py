"""The core must not depend on MkDocs."""

import subprocess
import sys


def test_core_imports_without_mkdocs() -> None:
    code = (
        "import sys\n"
        "sys.modules['mkdocs'] = None\n"
        "import mkdocs_exporter.core.aggregator\n"
        "import mkdocs_exporter.core.browser\n"
        "import mkdocs_exporter.core.renderer\n"
        "import mkdocs_exporter.core.runner\n"
        "import mkdocs_exporter.core.server\n"
        "import mkdocs_exporter.core.themes\n"
    )

    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
