from __future__ import annotations

from abc import abstractmethod

from mkdocs.structure.files import File
from mkdocs.theme import Theme as BaseTheme


class Theme:
  """A theme."""


  def __init__(self, theme: BaseTheme):
    """The constructor."""

    self.theme = theme


  @abstractmethod
  def preprocess(self, preprocessor):
    """Preprocess the page especially for this theme."""

    raise NotImplementedError()


  @abstractmethod
  def button(self, preprocessor, title: str, icon: str, attributes: dict = {}):
    """Inserts a custom themed button."""

    raise NotImplementedError()


  def stylesheet(self, stylesheet: File, content: str) -> str:
    """Transforms a stylesheet."""

    return content
