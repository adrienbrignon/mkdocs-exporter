/**
 * MkDocs Exporter: Material for MkDocs adjustments (loaded before the theme's scripts).
 *
 * Material renders Mermaid diagrams asynchronously, replacing each `pre.mermaid` block by
 * a `div.mermaid` element: documents are paginated once every diagram has been rendered.
 */
(() => {
  let expected = 0;

  document.addEventListener('DOMContentLoaded', () => {
    expected = document.querySelectorAll('pre.mermaid, div.mermaid').length;
  });

  window.MkDocsExporterTheme = {
    settle: async () => {
      const deadline = Date.now() + 10000;
      const rendered = () => document.querySelectorAll('div.mermaid').length;

      while (rendered() < expected && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 50));
      }
    },
  };
})();
