window.PagedConfig = {

  /**
   * The settings.
   */
  auto: true,
  settings: {
    maxChars: 1e32
  },

  /**
   * Invoked before rendering the pages...
   */
  before: async () => {
    if (window.MkDocsExporter) {
      if (typeof window.MkDocsExporter.render === 'function') {
        try {
          await window.MkDocsExporter.render(this);
        } catch (error) {
          console.error('[mkdocs-exporter] Failed to invoke render function:', error);
        }
      }
    }
  },

  /**
   * Invoked once all pages have been rendered.
   */
  after: () => {
    if ('__MKDOCS_EXPORTER__' in window) {
      const pages = document.getElementsByClassName('pagedjs_pages')[0];

      if (pages) {
        if ('pages' in __MKDOCS_EXPORTER__) {
          pages.style.setProperty('--pagedjs-page-count', __MKDOCS_EXPORTER__.pages);
        }

        if ('page' in __MKDOCS_EXPORTER__ && pages.children[0]) {
          pages.children[0].style.setProperty('counter-set', `page ${__MKDOCS_EXPORTER__.page}`);
        }
      }
    }

    document.body.setAttribute('mkdocs-exporter-pages', document.getElementsByClassName('pagedjs_page').length);
    document.body.setAttribute('mkdocs-exporter', 'true');
  }

};
