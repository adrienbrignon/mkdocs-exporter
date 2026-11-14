"""Tests of the package's import-time requirements."""

import subprocess
import sys


def test_plugin_imports_without_mkdocs_material() -> None:
    code = (
        "import sys\n"
        "sys.modules['material'] = None\n"
        "sys.modules['materialx'] = None\n"
        "import mkdocs_exporter.plugin\n"
    )

    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
