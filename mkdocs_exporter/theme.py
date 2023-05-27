from abc import abstractmethod
from mkdocs.theme import Theme as BaseTheme


class Theme:
  """A theme."""


  def __init__(self, theme: BaseTheme):
    """The constructor."""

    self.theme = theme


  @abstractmethod
  def preprocess():
    """Preprocess the page especially for this theme."""

    raise NotImplementedError()


  @abstractmethod
  def button(self, preprocessor, title: str, icon: str, attributes: dict = {}):
    """Inserts a custom themed button."""

    raise NotImplementedError()


  def stylesheet(self, css: str) -> str:
    """Transforms a stylesheet."""

    return css
