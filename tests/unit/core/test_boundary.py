import subprocess
import sys


def test_core_imports_without_mkdocs() -> None:
    code = (
        "import importlib, pkgutil, sys\n"
        "sys.modules['mkdocs'] = None\n"
        "import mkdocs_exporter.core as core\n"
        "for module in pkgutil.walk_packages(core.__path__, 'mkdocs_exporter.core.'):\n"
        "    importlib.import_module(module.name)\n"
    )

    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True)
