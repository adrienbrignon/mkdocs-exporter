import asyncio

from typing import Self
from tempfile import NamedTemporaryFile
from mkdocs_exporter.logging import logger
from playwright.async_api import async_playwright


class Browser:
  """A web browser instance."""

  args = [
    '--allow-file-access-from-files'
  ]
  """The browser's arguments..."""


  @property
  def launched(self):
    """Has the browser been launched?"""

    return self._launched


  def __init__(self):
    """The constructor."""

    self._launched = False
    self.lock = asyncio.Lock()


  async def launch(self) -> Self:
    """Launches the browser."""

    if self.launched:
      return self

    async with self.lock:
      if self.launched:
        return self

      logger.info('[PDF] Launching browser...')

      self.playwright = await async_playwright().start()
      self.browser = await self.playwright.chromium.launch(headless=True, args=self.args)
      self.context = await self.browser.new_context()

      self._launched = True

    return self


  async def close(self) -> Self:
    """Closes the browser."""

    if self.context:
      await self.context.close()
    if self.browser:
      await self.browser.close()
    if self.playwright:
      await self.playwright.stop()

    return self


  async def print(self, html: str) -> bytes:
    """Prints some HTML to PDF."""

    page = await self.context.new_page()

    with NamedTemporaryFile(suffix='.html', mode='w+', encoding='utf-8') as file:
      file.write(html)
      file.flush()

      await page.goto('file://' + file.name, wait_until='networkidle')
      await page.locator('.pagedjs_pages').wait_for(timeout=30000)

    pdf = await page.pdf(prefer_css_page_size=True, print_background=True, display_header_footer=False)

    await page.close()

    return pdf
