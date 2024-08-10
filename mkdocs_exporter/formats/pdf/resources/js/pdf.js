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
      const fn = window.MkDocsExporter.before ?? window.MkDocsExporter.render;

      if (typeof fn === 'function') {
        try {
          await fn(this);
        } catch (error) {
          console.error(`[mkdocs-exporter] Failed to invoke 'before' function:`, error);
        }
      }
    }
  },

  /**
   * Invoked once all pages have been rendered.
   */
  after: async () => {
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

    if (window.MkDocsExporter) {
      const fn = window.MkDocsExporter.after;

      if (typeof fn === 'function') {
        try {
          await fn(this);
        } catch (error) {
          console.error(`[mkdocs-exporter] Failed to invoke 'after' function:`, error);
        }
      }
    }

    document.body.setAttribute('mkdocs-exporter', 'true');
  }

};
