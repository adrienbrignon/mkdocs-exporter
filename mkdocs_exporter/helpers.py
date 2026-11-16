from collections import UserDict
from typing import Any


def resolve(value: Any, *args: Any, **kwargs: Any) -> Any:
    """Resolves callables (recursively, through lists and dictionaries)."""

    if callable(value):
        return resolve(value(*args, **kwargs), *args, **kwargs)
    if isinstance(value, list):
        return [resolve(item, *args, **kwargs) for item in value]
    if isinstance(value, (dict, UserDict)):
        return {key: resolve(item, *args, **kwargs) for key, item in value.items()}

    return value
