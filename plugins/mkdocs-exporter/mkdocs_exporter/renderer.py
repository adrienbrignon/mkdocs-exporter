from abc import abstractmethod
from mkdocs_exporter.page import Page


class Renderer:
  """A generic renderer."""


  @abstractmethod
  def render(self, page: Page) -> any:
    """Renders the given page."""

    raise NotImplementedError()
