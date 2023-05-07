import os


from mkdocs.plugins import BasePlugin
from mkdocs_exporter.page import Page
from mkdocs_exporter.preprocessor import Preprocessor
from mkdocs_exporter.plugins.extras.config import Config


class Plugin(BasePlugin[Config]):
  """The plugin."""


  def on_post_page(self, html: str, page: Page, **kwargs) -> None | str:
    """Invoked after a page has been built."""

    if 'pdf' not in self.config.downloads or 'pdf' not in page.formats:
      return html

    preprocessor = Preprocessor()
    download = page.title + '.pdf'
    href = os.path.relpath(page.formats['pdf'], page.url)

    preprocessor.preprocess(html)
    preprocessor.button(title='Download as PDF', href=href, download=download, icon='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="m14 2 6 6v12a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8m4 18V9h-5V4H6v16h12m-6-1-4-4h2.5v-3h3v3H16l-4 4Z"/></svg>')

    return preprocessor.done()
