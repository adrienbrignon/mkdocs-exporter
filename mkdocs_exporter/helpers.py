from collections import UserDict


def resolve(object, *args, **kwargs):
  """Resolves a callable."""

  if callable(object):
    return resolve(object(*args, **kwargs), *args, **kwargs)
  if isinstance(object, list):
    return [resolve(v, *args, **kwargs) for v in object]
  if isinstance(object, (dict, UserDict)):
    return {k: resolve(v, *args, **kwargs) for k, v in object.items()}

  return object
