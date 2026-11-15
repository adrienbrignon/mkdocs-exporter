(() => {
  const EXCLUDED = '.mkdocs-exporter-front-cover, .mkdocs-exporter-back-cover, .mkdocs-exporter-toc';

  const text = (element) => element.textContent.replace(/\s+/g, ' ').trim();

  /**
   * The `@page` rules setting a top margin, in order.
   */
  const pageRules = () => {
    const rules = [];
    const walk = (list) => {
      for (const rule of list) {
        if (rule instanceof CSSPageRule) {
          const value = rule.style.getPropertyValue('margin-top');

          if (value) {
            rules.push({ selector: rule.selectorText, marginTop: value });
          }
        } else if (rule instanceof CSSMediaRule) {
          if (matchMedia(rule.media.mediaText).matches) {
            walk(rule.cssRules);
          }
        } else if (rule instanceof CSSImportRule) {
          try {
            if (!rule.media.mediaText || matchMedia(rule.media.mediaText).matches) {
              walk(rule.styleSheet.cssRules);
            }
          } catch (error) { /* Cross-origin stylesheet. */ }
        } else if (rule.cssRules) {
          walk(rule.cssRules);
        }
      }
    };

    for (const sheet of document.styleSheets) {
      try {
        if (!sheet.disabled && (!sheet.media.mediaText || matchMedia(sheet.media.mediaText).matches)) {
          walk(sheet.cssRules);
        }
      } catch (error) { /* Cross-origin stylesheet. */ }
    }

    return rules;
  };

  /**
   * Measures the print layout. Chromium lays printed documents out in a "stitched"
   * coordinate space: page areas (without margins) stacked vertically, the root element
   * having one fragment per page.
   */
  const measure = () => {
    const root = [...document.documentElement.getClientRects()];
    const tops = root.map((rect) => rect.top);
    const pageOf = (y) => {
      let low = 0;
      let high = tops.length - 1;

      while (low < high) {
        const middle = (low + high + 1) >> 1;

        if (tops[middle] <= y + 0.5) {
          low = middle;
        } else {
          high = middle - 1;
        }
      }

      return low;
    };
    const span = (element) => {
      const rects = element ? [...element.getClientRects()].filter((r) => r.width || r.height) : [];

      if (rects.length === 0) {
        return null;
      }

      return [pageOf(rects[0].top), pageOf(rects[rects.length - 1].bottom - 1)];
    };

    const parts = [...document.querySelectorAll('.mkdocs-exporter-part')].map((part) => {
      const headings = [];

      for (const heading of part.querySelectorAll('h1, h2, h3, h4, h5, h6')) {
        if (heading.closest(EXCLUDED) || heading.getClientRects().length === 0) {
          continue;
        }

        const top = heading.getBoundingClientRect().top;
        const page = pageOf(top);

        headings.push({
          level: Number(heading.tagName.substring(1)),
          id: heading.id || null,
          title: text(heading),
          page,
          top: Math.max(0, top - tops[page]),
        });
      }

      return {
        id: part.id,
        span: span(part),
        front: span(part.querySelector(':scope > .mkdocs-exporter-front-cover')),
        back: span(part.querySelector(':scope > .mkdocs-exporter-back-cover')),
        headings,
      };
    });

    window.__MKDOCS_EXPORTER_LAYOUT__ = {
      pages: tops.length,
      width: root.length ? root[0].width : 0,
      parts,
      toc: span(document.querySelector('.mkdocs-exporter-toc')),
      blanks: [...document.querySelectorAll('.mkdocs-exporter-blank')].map((blank) => span(blank) || [pageOf(blank.getBoundingClientRect().top)]),
      pageRules: pageRules(),
    };
  };

  matchMedia('print').addEventListener('change', (event) => {
    if (!event.matches) {
      return;
    }

    try {
      measure();
    } catch (error) {
      window.__MKDOCS_EXPORTER_LAYOUT__ = { error: String((error && error.stack) || error) };
    }
  });

  const apply = (patch) => {
    if (typeof patch.toc === 'string') {
      const toc = document.querySelector('.mkdocs-exporter-toc');

      if (toc) {
        toc.innerHTML = patch.toc;
      }
    }

    if (Array.isArray(patch.blanks)) {
      document.querySelectorAll('.mkdocs-exporter-blank').forEach((blank) => blank.remove());

      for (const id of patch.blanks) {
        const blank = document.createElement('div');

        blank.className = 'mkdocs-exporter-blank';
        document.getElementById(id).before(blank);
      }
    }

    if (typeof patch.css === 'string') {
      let style = document.getElementById('mkdocs-exporter-generated');

      if (!style) {
        style = document.createElement('style');
        style.id = 'mkdocs-exporter-generated';
        document.head.appendChild(style);
      }

      style.textContent = patch.css;
    }
  };

  window.__MKDOCS_EXPORTER_BOOK__ = { apply };
})();
