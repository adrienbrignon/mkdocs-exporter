from __future__ import annotations

import os
import asyncio

from tempfile import NamedTemporaryFile
from playwright.async_api import async_playwright

from mkdocs_exporter.logging import logger


class Browser:
  """A web browser instance."""

  args = [
    '--disable-background-timer-throttling',
    '--disable-renderer-backgrounding',
    '--allow-file-access-from-files',
    '--font-render-hinting=none'
  ]
  """The browser's arguments..."""


  @property
  def launched(self):
    """Has the browser been launched?"""

    return self._launched


  def __init__(self, options: dict = {}):
    """The constructor."""

    self.browser = None
    self.context = None
    self._launched = False
    self.playwright = None
    self.lock = asyncio.Lock()
    self.debug = options.get('debug', False)
    self.headless = options.get('headless', True)
    self.timeout = options.get('timeout', 60_000)
    self.args = self.args + options.get('args', [])
    self.levels = {
      'warn': 'warning',
      'error': 'error',
      'info': 'info',
      'debug': 'debug'
    }


  async def launch(self) -> Browser:
    """Launches the browser."""

    if self.launched:
      return self

    async with self.lock:
      if self.launched:
        return self

      logger.info('[mkdocs-exporter.pdf] Launching browser...')

      self.playwright = await async_playwright().start()
      self.browser = await self.playwright.chromium.launch(headless=self.headless, args=self.args)
      self.context = await self.browser.new_context()

      self.context.on('console', self.log)

      self._launched = True

    return self


  async def close(self) -> Browser:
    """Closes the browser."""

    if self.context:
      await self.context.close()
    if self.browser:
      await self.browser.close()
    if self.playwright:
      await self.playwright.stop()

    self._launched = False

    return self


  async def print(self, html: str) -> tuple[bytes, int]:
    """Prints some HTML to PDF and returns the PDF and the number of pages printed."""

    pages = 0
    context = await self.context.new_page()
    file = NamedTemporaryFile(suffix='.html', mode='w+', encoding='utf-8', delete=False)

    file.write(html)
    file.close()

    await context.goto('file://' + file.name, wait_until='networkidle', timeout=self.timeout)
    await context.locator('body[mkdocs-exporter="true"]').wait_for(timeout=self.timeout)

    pages = int(await context.locator('body').get_attribute('mkdocs-exporter-pages', timeout=self.timeout) or 0)
    pdf = await context.pdf(prefer_css_page_size=True, print_background=True, display_header_footer=False)

    await context.close()

    os.unlink(file.name)

    return (pdf, pages)


  async def log(self, msg):
    """Logs a message coming from the browser."""

    prefix = '[mkdocs-exporter]'
    text = msg.text
    level = self.levels.get(msg.type, 'info')

    if text.startswith(prefix):
      text = msg.text[len(prefix):].strip()

    if self.debug or level == 'error':
      getattr(logger, level)(f"[mkdocs-exporter.pdf.browser] ({msg.type}) {await msg.page.title()}\n{text}")
