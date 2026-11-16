# JavaScript hooks

Scripts run in documents ([`formats.pdf.scripts`](../guide/styles-and-scripts.md#scripts), or the website's own scripts) can define hooks in `window.MkDocsExporter`, which the exporter awaits before printing:

```javascript
window.MkDocsExporter = {
  before: async () => {},
  render: async () => {},
  after: async () => {},
};
```

| Hook | When |
|---|---|
| `before` | Once the page is loaded, with its fonts, images, MathJax formulas and theme ready (e.g. Material for MkDocs' diagrams) |
| `render` | After `before`: the place to draw content (diagrams, charts...) |
| `after` | Last, right before printing, after [`formats.pdf.browser.delay`](../guide/documents.md#browser) |

- Every hook is optional, takes no argument, and may return a promise, which is awaited.
- Hooks run once per document: a [book](../guide/books.md) runs them once, its pages being a single HTML document.
- Hooks run in documents only: the website doesn't call them.
- An error in a hook (thrown or rejected) is logged as a warning: the document is still printed, but not [cached](../how-to/performance.md#cache).
- Waiting for fonts, images, formulas and diagrams gives up after 10 seconds, with a warning.
- Preparing the page is bounded by `formats.pdf.browser.timeout` (60 seconds by default): a hook that never returns makes the page fail with "Timed out".
