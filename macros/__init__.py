import importlib.metadata

import mkdocs_exporter


def define_env(env):
    """
    A hook for the MkDocs Macros plugin.
    """

    env.variables["version"] = importlib.metadata.version(mkdocs_exporter.__name__)
