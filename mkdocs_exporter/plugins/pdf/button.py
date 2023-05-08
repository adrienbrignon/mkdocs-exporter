import os

from textwrap import dedent
from mkdocs_exporter.page import Page


def href(page: Page) -> str:
  """The button's 'href' attribute."""

  return os.path.relpath(page.formats['pdf'], page.url)


def download(page: Page) -> str:
  """The button's 'download' attribute."""

  return page.title + os.path.extsep + 'pdf'


def icon(page: Page) -> str:
  """The button's icon."""

  return dedent('''
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
      <path d="M14,2L20,8V20A2,2 0 0,1 18,22H6A2,2 0 0,1 4,20V4A2,2 0 0,1 6,2H14M18,20V9H13V4H6V20H18M12,19L8,15H10.5V12H13.5V15H16L12,19Z" />
    </svg>
  ''')
