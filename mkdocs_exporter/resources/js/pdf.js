window.PagedConfig = {

  /**
   * The settings.
   */
  settings: {
    maxChars: 1e9
  },

  /**
   * Invoked once all pages have been rendered.
   */
  after: () => {
    document.body.setAttribute('mkdocs-exporter', 'true')
  },

};
