/**
 * An interface with the MkDocs Exporter plugin.
 */
window.MkDocsExporter = {

  /**
   * Render the page...
   */
  render: async () => {
    if (window.MathJax) {
      if (typeof window.MathJax.typesetPromise === 'function') {
        await window.MathJax.typesetPromise();
      }
    }

    if (window.mermaid) {
      if (typeof window.mermaid.run === 'function') {
        for (const element of document.querySelectorAll('.mermaid > code')) {
          const container = document.createElement('div');

          container.className = 'mermaid';

          await mermaid.run({ nodes: [element] });

          element.parentElement.appendChild(container);
          container.appendChild(element.children[0]);
          element.remove();
        }
      }
    }
  }

};
