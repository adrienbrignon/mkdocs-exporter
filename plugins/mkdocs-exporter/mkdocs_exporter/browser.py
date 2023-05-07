import asyncio

from typing import Self
from tempfile import NamedTemporaryFile
from mkdocs_exporter.logging import logger
from playwright.async_api import async_playwright


class Browser:
  """A web browser instance."""


  def __init__(self):
    """The constructor."""

    self._launched = False
    self.lock = asyncio.Lock()


  async def launch(self) -> Self:
    """Launches the browser."""

    async with self.lock:
      if self.launched:
        return self

      logger.info('Launching browser...')

      self.playwright = await async_playwright().start()
      self.browser = await self.playwright.chromium.launch()
      self.context = await self.browser.new_context()
      self._launched = True

    return self


  @property
  def launched(self):
    """Has the browser been launched?"""

    return self._launched


  async def print(self, html: str) -> bytes:
    """Prints some HTML to PDF."""

    page = await self.context.new_page()

    with NamedTemporaryFile(suffix='.html', mode='w+', encoding='utf-8') as file:
      file.write(html)
      file.flush()

      await page.goto('file://' + file.name, wait_until='networkidle')
      await page.locator('.md-content > .md-content__inner').wait_for(timeout=30000)

    bytes = await page.pdf(width='21cm', height='29.7cm', prefer_css_page_size=True, print_background=True)

    await page.close()

    return bytes
