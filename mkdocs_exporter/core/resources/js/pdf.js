/**
 * MkDocs Exporter: gets pages ready to be printed and reports when they are.
 *
 * Contract with the exporter (Python side):
 * - `window.__MKDOCS_EXPORTER__` holds options (`delay`);
 * - once ready, `body[mkdocs-exporter]` is set to `true`, or to `error` (with the reason in
 *   `window.__MKDOCS_EXPORTER_ERROR__`), and `window.__MKDOCS_EXPORTER_READY__` (a promise)
 *   resolves with that state;
 * - uncaught errors are recorded with the phase they occurred in (`loading`, `rendering`,
 *   `printing`) in `window.__MKDOCS_EXPORTER_ERRORS__`; errors thrown by the hooks below
 *   are recorded with the `hook` phase and don't stop the rendering.
 *
 * This script must be loaded in the document's head, before the website's scripts.
 *
 * Users can define `window.MkDocsExporter.before`, `.render` and `.after`: they are
 * awaited, in this order, once the page and its resources are loaded and before printing.
 *
 * Pages are given the body's font family, and `html[data-mkdocs-exporter-page-background]`
 * is set when a `@page` rule sets a background (see `canvas`).
 */
(() => {
  const errors = [];
  let phase = 'loading';
  let ready;

  window.__MKDOCS_EXPORTER_ERRORS__ = errors;
  window.__MKDOCS_EXPORTER_READY__ = new Promise((resolve) => {
    ready = resolve;
  });

  window.addEventListener('error', (event) => {
    if (event instanceof ErrorEvent) {
      errors.push({ phase, message: String((event.error && event.error.stack) || event.message) });
    }
  }, true);

  window.addEventListener('unhandledrejection', (event) => {
    errors.push({ phase, message: String((event.reason && event.reason.stack) || event.reason) });
  });

  const options = () => window.__MKDOCS_EXPORTER__ || {};
  const hooks = () => window.MkDocsExporter || {};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

  const signal = (state) => {
    document.body.setAttribute('mkdocs-exporter', state);
    ready(state);
  };

  const call = async (name, ...args) => {
    const hook = hooks()[name];

    if (typeof hook !== 'function') {
      return;
    }

    try {
      await hook(...args);
    } catch (error) {
      errors.push({ phase: 'hook', message: `MkDocsExporter.${name}: ${(error && error.stack) || error}` });
    }
  };

  /**
   * Waits for fonts, images, MathJax and the theme (bounded, to never block forever).
   */
  const settle = async () => {
    const images = [...document.images].map((image) => {
      image.loading = 'eager';

      return image.complete
        ? null
        : new Promise((resolve) => {
          image.addEventListener('load', resolve, { once: true });
          image.addEventListener('error', resolve, { once: true });
        });
    });

    const theme = window.MkDocsExporterTheme || {};
    const pending = [document.fonts ? document.fonts.ready : null, ...images];

    if (typeof theme.settle === 'function') {
      pending.push(theme.settle());
    }

    if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
      pending.push(window.MathJax.startup.promise);
    }

    const settled = await Promise.race([
      Promise.all(pending).then(() => true),
      sleep(10000).then(() => false),
    ]);

    if (!settled) {
      errors.push({
        phase: 'hook',
        message: 'Gave up waiting for fonts, images or diagrams after 10 seconds',
      });
    }
  };

  /**
   * Does a `@page` rule set a background? Rules are looked for whatever media they apply
   * to (pages are in screen media until printed).
   */
  const pageBackgrounds = () => {
    const properties = ['background', 'background-color', 'background-image'];
    const walk = (rules) => {
      for (const rule of rules) {
        if (rule instanceof CSSPageRule) {
          if (properties.some((property) => rule.style.getPropertyValue(property))) {
            return true;
          }

          continue;
        }

        let children = null;

        try {
          children = rule instanceof CSSImportRule ? rule.styleSheet && rule.styleSheet.cssRules : rule.cssRules;
        } catch (error) { /* Cross-origin stylesheet. */ }

        if (children && walk(children)) {
          return true;
        }
      }

      return false;
    };

    for (const sheet of document.styleSheets) {
      try {
        if (walk(sheet.cssRules)) {
          return true;
        }
      } catch (error) { /* Cross-origin stylesheet. */ }
    }

    return false;
  };

  /**
   * Prepares the page context:
   * - margin boxes inherit from the root element rather than from the body: pages are given
   *   the body's font family, with a `@page` rule coming before every other (the font size
   *   is left alone: `em` lengths of `@page` rules, such as margins, depend on it);
   * - printed natively, the canvas (the background of the root and body) is painted over
   *   whole pages, hiding the backgrounds of `@page` rules (e.g. full-bleed covers): when a
   *   `@page` rule sets one, the root is marked for `base.css` to make the root and body
   *   transparent in print. Otherwise, the canvas is left alone: its color in print can't
   *   be read before printing (e.g. dark themes printed on white).
   */
  const canvas = () => {
    const style = document.createElement('style');

    style.textContent = `@page { font-family: ${getComputedStyle(document.body).fontFamily}; }`;
    document.head.prepend(style);

    if (pageBackgrounds()) {
      document.documentElement.setAttribute('data-mkdocs-exporter-page-background', '');
    }
  };

  const run = async () => {
    try {
      phase = 'rendering';

      await settle();
      await call('before');
      await call('render');

      if (options().delay) {
        await sleep(options().delay);
      }

      await call('after');

      canvas();

      // Keep the website's scripts from reacting to the upcoming print.
      for (const event of ['beforeprint', 'afterprint', 'resize', 'scroll']) {
        window.addEventListener(event, (e) => e.stopImmediatePropagation(), true);
      }

      phase = 'printing';
      signal('true');
    } catch (error) {
      window.__MKDOCS_EXPORTER_ERROR__ = String((error && error.stack) || error);
      signal('error');
    }
  };

  if (document.readyState === 'complete') {
    run();
  } else {
    window.addEventListener('load', run, { once: true });
  }
})();
