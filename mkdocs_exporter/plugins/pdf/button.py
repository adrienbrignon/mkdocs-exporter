import os

from mkdocs_exporter.page import Page


def enabled(page: Page, **kwargs) -> bool:
  """Is the button enabled?"""

  return 'pdf' in page.formats


def href(page: Page, **kwargs) -> str:
  """The button's 'href' attribute."""

  return os.path.relpath(page.formats['pdf'], page.url)


def download(page: Page, **kwargs) -> str:
  """The button's 'download' attribute."""

  return page.title + os.path.extsep + 'pdf'


def icon(page: Page, **kwargs) -> str:
  """The button's icon."""

  return page.meta.get('pdf-icon', 'material-file-download-outline')
