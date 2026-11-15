/**
 * MkDocs Exporter: drives Paged.js and reports the outcome to the exporter.
 *
 * Contract with the exporter (Python side):
 * - `window.__MKDOCS_EXPORTER__` holds options (`pagedjs`, `hide`, `delay`, `page`, `pages`);
 * - once done, `body[mkdocs-exporter]` is set to `true` (with the layout in
 *   `window.__MKDOCS_EXPORTER_RESULT__`) or to `error` (with the reason in
 *   `window.__MKDOCS_EXPORTER_ERROR__`);
 * - uncaught errors are recorded with the phase they occurred in (`loading`, `rendering`,
 *   `paginating`, `printing`) in `window.__MKDOCS_EXPORTER_ERRORS__`; errors thrown by
 *   the hooks below are recorded with the `hook` phase and don't stop the rendering.
 *
 * This script must be loaded in the document's head, before the website's scripts.
 *
 * Users can define `window.MkDocsExporter.before`, `.render` (awaited before pagination)
 * and `.after` (awaited after pagination). Paged.js (`window.Paged`) is available from
 * `before` on, e.g. to register handlers with `Paged.registerHandlers()`.
 */
(() => {
  const COVERS = {
    front: '.mkdocs-exporter-front-cover',
    back: '.mkdocs-exporter-back-cover',
  };

  const errors = [];
  let phase = 'loading';

  window.__MKDOCS_EXPORTER_ERRORS__ = errors;

  window.addEventListener('error', (event) => {
    if (event instanceof ErrorEvent) {
      errors.push({ phase, message: String((event.error && event.error.stack) || event.message) });
    }
  }, true);

  window.addEventListener('unhandledrejection', (event) => {
    errors.push({ phase, message: String((event.reason && event.reason.stack) || event.reason) });
  });

  // Paged.js can't paginate shadow trees: keep them open so that they can be flattened.
  const attachShadow = Element.prototype.attachShadow;

  Element.prototype.attachShadow = function (init) {
    return attachShadow.call(this, { ...init, mode: 'open' });
  };

  const options = () => window.__MKDOCS_EXPORTER__ || {};
  const hooks = () => window.MkDocsExporter || {};
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
  const squash = (text) => (text || '').replace(/\s+/g, '');

  const signal = (state) => {
    document.body.setAttribute('mkdocs-exporter', state);
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
   * Waits for fonts, images and MathJax (bounded, to never block rendering forever).
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
   * Removes elements that must not appear in the document.
   *
   * They are hidden by CSS until now so that the website's scripts can initialize, and
   * removed before pagination because Paged.js repeats `position: fixed` elements on
   * every page, regardless of their ancestors' visibility.
   */
  const prune = () => {
    for (const selector of options().hide || []) {
      for (const element of document.querySelectorAll(selector)) {
        element.remove();
      }
    }
  };

  /**
   * Replaces elements hosting a shadow tree by a copy of that tree (e.g. diagrams).
   */
  const flatten = (root) => {
    for (const host of root.querySelectorAll('*')) {
      if (!host.shadowRoot) {
        continue;
      }

      flatten(host.shadowRoot);

      const copy = document.createElement('div');

      for (const attribute of host.attributes) {
        copy.setAttribute(attribute.name, attribute.value);
      }

      copy.innerHTML = host.shadowRoot.innerHTML;
      host.replaceWith(copy);
    }
  };

  /**
   * Exposes the current section (first or second-level heading) of each page as a CSS
   * custom property, for headers and footers: the first heading of the page, or the
   * last one of the previous pages (like `string()`, which Paged.js mishandles).
   */
  const sections = () => {
    const quote = (text) => `"${text.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\s+/g, ' ').trim()}"`;
    const excluded = '.mkdocs-exporter-front-cover, .mkdocs-exporter-back-cover, .mkdocs-exporter-toc';
    let current = null;

    for (const page of document.querySelectorAll('.pagedjs_page')) {
      const headings = [...page.querySelectorAll('.pagedjs_page_content :is(h1, h2)')]
        .filter((heading) => !heading.closest(excluded));
      const title = (heading) => {
        const clone = heading.cloneNode(true);

        clone.querySelectorAll('.headerlink, .anchorlink').forEach((link) => link.remove());

        return clone.textContent;
      };

      if (headings.length > 0) {
        page.style.setProperty('--mkdocs-exporter-section', quote(title(headings[0])));
        current = title(headings[headings.length - 1]);
      } else if (current !== null) {
        page.style.setProperty('--mkdocs-exporter-section', quote(current));
      }
    }
  };

  /**
   * Applies the page numbering of the aggregated document.
   */
  const number = () => {
    const container = document.querySelector('.pagedjs_pages');
    const { page, pages } = options();

    if (!container) {
      return;
    }
    if (typeof pages === 'number') {
      container.style.setProperty('--pagedjs-page-count', pages);
    }
    if (typeof page === 'number' && container.firstElementChild) {
      container.firstElementChild.style.setProperty('counter-set', `page ${page}`);
    }
  };

  /**
   * Measures the rendered document.
   */
  const measure = () => {
    const pages = [...document.querySelectorAll('.pagedjs_page')];
    const indexes = new Map(pages.map((page, index) => [page, index]));
    const coverPages = {};
    const excluded = '.mkdocs-exporter-front-cover, .mkdocs-exporter-back-cover, .mkdocs-exporter-toc';
    const locate = (element) => {
      const page = element.closest('.pagedjs_page');

      if (!page || element.closest(excluded)) {
        return null;
      }

      const top = element.getBoundingClientRect().top - page.getBoundingClientRect().top;

      return { page: indexes.get(page), top: Math.max(0, top) };
    };

    const anchors = {};

    for (const element of document.querySelectorAll('.pagedjs_page [id]')) {
      const position = !(element.id in anchors) && locate(element);

      if (position) {
        anchors[element.id] = position;
      }
    }

    const headings = [];

    for (const element of document.querySelectorAll('.pagedjs_page_content :is(h1, h2, h3, h4, h5, h6)')) {
      const position = !element.hasAttribute('data-split-from') && locate(element);

      if (!position) {
        continue;
      }

      const clone = element.cloneNode(true);

      clone.querySelectorAll('.headerlink, .anchorlink').forEach((link) => link.remove());

      headings.push({
        level: Number(element.tagName.substring(1)),
        title: clone.textContent.replace(/\s+/g, ' ').trim(),
        id: element.id || null,
        ...position,
      });
    }

    for (const [location, selector] of Object.entries(COVERS)) {
      coverPages[location] = pages.filter((page) => {
        const content = page.querySelector('.pagedjs_page_content') || page;
        const covers = [...content.querySelectorAll(selector)];

        if (covers.length === 0) {
          return false;
        }

        const media = 'img, svg, video, canvas, table, pre';
        const visible = (elements) => [...elements].filter((e) => e.getClientRects().length > 0);
        const coverMedia = covers.reduce((n, c) => n + visible(c.querySelectorAll(media)).length, 0);

        return squash(content.innerText) === squash(covers.map((c) => c.innerText).join(''))
          && visible(content.querySelectorAll(media)).length === coverMedia;
      }).length;
    }

    return { pages: pages.length, coverPages, anchors, headings };
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

      flatten(document);
      prune();

      phase = 'paginating';
      const flow = await window.PagedPolyfill.preview();

      // Paged.js has moved the content into pages: keep the website's scripts from
      // reacting to the upcoming print (they would look for elements that moved).
      for (const event of ['beforeprint', 'afterprint', 'resize', 'scroll']) {
        window.addEventListener(event, (e) => e.stopImmediatePropagation(), true);
      }

      number();
      sections();
      await call('after', flow);

      window.__MKDOCS_EXPORTER_RESULT__ = measure();
      phase = 'printing';
      document.body.setAttribute('mkdocs-exporter-pages', window.__MKDOCS_EXPORTER_RESULT__.pages);
      signal('true');
    } catch (error) {
      window.__MKDOCS_EXPORTER_ERROR__ = String((error && error.stack) || error);
      signal('error');
    }
  };

  window.PagedConfig = {
    auto: false,
    settings: { maxChars: 1e32 },
    after: run,
  };

  // Paged.js is loaded once the website's own scripts have initialized: some of them
  // break when its polyfills are already present (e.g. Bootstrap's modals).
  window.addEventListener('load', () => {
    const script = document.createElement('script');

    script.src = options().pagedjs;
    script.addEventListener('error', () => {
      window.__MKDOCS_EXPORTER_ERROR__ = `Failed to load Paged.js from ${script.src}`;
      signal('error');
    });

    document.head.appendChild(script);
  });
})();
