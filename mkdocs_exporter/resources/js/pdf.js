window.PagedConfig = {

  /**
   * The settings.
   */
  settings: {
    maxChars: 1e9
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
    document.body.setAttribute('mkdocs-exporter', 'true');
  }

};
