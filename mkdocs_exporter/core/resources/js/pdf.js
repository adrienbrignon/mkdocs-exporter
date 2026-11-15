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
 * The background of the page (`html` or `body`) and the body's font family are moved to
 * pages (see `canvas`), `base.css` making `html` and `body` transparent in print.
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
   * Gives pages the canvas color (the root's or body's background) and the body's font
   * family, with a `@page` rule coming before every other: printed natively, the canvas is
   * painted over the page, hiding the backgrounds of `@page` rules (e.g. full-bleed
   * covers), and margin boxes inherit from the root element rather than from the body.
   * The font size is left alone: `em` lengths of `@page` rules (margins) depend on it.
   */
  const canvas = () => {
    const declarations = [`font-family: ${getComputedStyle(document.body).fontFamily};`];

    for (const element of [document.documentElement, document.body]) {
      const color = getComputedStyle(element).backgroundColor;

      if (color && color !== 'transparent' && color !== 'rgba(0, 0, 0, 0)') {
        declarations.push(`background-color: ${color};`);
        break;
      }
    }

    const style = document.createElement('style');

    style.textContent = `@page { ${declarations.join(' ')} }`;
    document.head.prepend(style);
  };

  const run = async () => {
    try {
      phase = 'rendering';

      canvas();

      await settle();
      await call('before');
      await call('render');

      if (options().delay) {
        await sleep(options().delay);
      }

      await call('after');

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
