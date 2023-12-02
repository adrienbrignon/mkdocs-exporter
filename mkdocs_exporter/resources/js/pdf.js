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
        await window.MkDocsExporter.render(this);
      }
    }
  },

  /**
   * Invoked once all pages have been rendered.
   */
  after: () => {
    document.body.setAttribute('mkdocs-exporter', 'true');
  },

};
