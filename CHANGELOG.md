# Changelog

All notable changes to this project are documented in this file, and this project adheres to [Semantic Versioning](https://semver.org/).
Entries are generated from commit messages ([Conventional Commits](https://www.conventionalcommits.org/)) by [release-please](https://github.com/googleapis/release-please), in release pull requests where they can be edited; earlier entries follow [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [7.0.0-rc.1](https://github.com/adrienbrignon/mkdocs-exporter/compare/v6.2.0...v7.0.0-rc.1) (2026-11-16)


### ⚠ BREAKING CHANGES

* `formats.pdf.aggregators` is renamed `formats.pdf.books`, and `formats.pdf.aggregator` is deprecated in favor of it.
* **pdf:** combined documents are printed as a single document: the page counters of custom stylesheets are continuous, the pages of the table of contents show its title as `{page_title}`, and `Renderer.render` / `Renderer.render_all` no longer take rendering passes.
* Paged.js is no longer bundled. Stylesheets relying on Paged.js-only features (string-set, target-counter, running elements, footnotes, :blank, left/right breaks) need Paged.js to be added with `formats.pdf.scripts` (see the documentation).
* cover templates are no longer processed as Markdown (Markdown syntax and emoji shortcodes aren't converted), and they are no longer part of the website's HTML.
* internal modules (`mkdocs_exporter.preprocessor`, `mkdocs_exporter.renderer`, `mkdocs_exporter.themes`, `mkdocs_exporter.formats.pdf.{plugin,renderer,browser,aggregator}`) are removed; PDF documents are no longer generated while serving by default; the `exporter-pdf` plugin is no longer registered.
* `formats.pdf.stylesheets` only accepts CSS files; `.scss` and `.sass` files are rejected with a configuration error.

### Added

* `mkdocs-exporter-only` class for content of documents only ([7294dcc](https://github.com/adrienbrignon/mkdocs-exporter/commit/7294dcc9af3f1662c405d226b477c04c059b194d))
* drop Sass support ([0b78612](https://github.com/adrienbrignon/mkdocs-exporter/commit/0b78612958d925a2fc08664d3a6e40795cc45164))
* list combined documents in `books` ([af2537b](https://github.com/adrienbrignon/mkdocs-exporter/commit/af2537bbc600df4d82a35b31beab7d08a5afe6aa))
* **pdf:** a button downloading the book a page is part of ([107a517](https://github.com/adrienbrignon/mkdocs-exporter/commit/107a517794132a47803420db1eb506889d113243))
* **pdf:** bookmarks, internal links, table of contents and multiple aggregates ([91679ef](https://github.com/adrienbrignon/mkdocs-exporter/commit/91679eff8be7d4d90d6d4c53c9282286ec104b4d)), closes [#31](https://github.com/adrienbrignon/mkdocs-exporter/issues/31) [#46](https://github.com/adrienbrignon/mkdocs-exporter/issues/46) [#52](https://github.com/adrienbrignon/mkdocs-exporter/issues/52) [#67](https://github.com/adrienbrignon/mkdocs-exporter/issues/67) [#24](https://github.com/adrienbrignon/mkdocs-exporter/issues/24) [#74](https://github.com/adrienbrignon/mkdocs-exporter/issues/74)
* **pdf:** configurable headers and footers ([4b5e114](https://github.com/adrienbrignon/mkdocs-exporter/commit/4b5e114f3826465c6248bdbda2760e4ad51c4579)), closes [#84](https://github.com/adrienbrignon/mkdocs-exporter/issues/84) [#66](https://github.com/adrienbrignon/mkdocs-exporter/issues/66)
* **pdf:** document information, language and smaller combined documents ([02b4c57](https://github.com/adrienbrignon/mkdocs-exporter/commit/02b4c57090e5996543162e3ed86e7a321cbaf322))
* **pdf:** keep the browser open between rebuilds while serving ([2b9bb13](https://github.com/adrienbrignon/mkdocs-exporter/commit/2b9bb13742300c9e25f6d3c7385c68132957a5ff))
* **pdf:** optionally insert page titles in documents ([4eb4049](https://github.com/adrienbrignon/mkdocs-exporter/commit/4eb40491a85817288cec4fccf733177932d308c7)), closes [#53](https://github.com/adrienbrignon/mkdocs-exporter/issues/53)
* **pdf:** pages can turn their table of contents on or off ([9c7a1f8](https://github.com/adrienbrignon/mkdocs-exporter/commit/9c7a1f8db5574c3ff6129f951da8b8a7fe1f8281))
* **pdf:** print combined documents as a single document ([0e3abfb](https://github.com/adrienbrignon/mkdocs-exporter/commit/0e3abfb5880d8c393baa17327ecf4797e9dbfde1))
* **pdf:** reuse unchanged documents from a cache ([b113cc9](https://github.com/adrienbrignon/mkdocs-exporter/commit/b113cc91fa51ea027ef2d6177d722b46a8bfd1ba))
* **pdf:** start documents of pages with a table of contents of their headings ([cc5fbda](https://github.com/adrienbrignon/mkdocs-exporter/commit/cc5fbdad39ca4932bcf6282b4370af147753904f)), closes [#24](https://github.com/adrienbrignon/mkdocs-exporter/issues/24)
* print documents natively with Chromium, without Paged.js ([b7999c8](https://github.com/adrienbrignon/mkdocs-exporter/commit/b7999c89c98dad9dcf34537da503b3ca017e1e5f))
* render cover pages as Jinja templates, outside of Markdown ([00b4575](https://github.com/adrienbrignon/mkdocs-exporter/commit/00b4575078ea3528cf336f154b494702230f5514)), closes [#17](https://github.com/adrienbrignon/mkdocs-exporter/issues/17) [#50](https://github.com/adrienbrignon/mkdocs-exporter/issues/50)


### Fixed

* **cache:** ignore bytecode when fingerprinting the package ([4bc22c8](https://github.com/adrienbrignon/mkdocs-exporter/commit/4bc22c8e353a4f96865dd39fe774bea8d3377f05))
* **css:** leave invalid or unchanged stylesheets as they are ([59e8fcf](https://github.com/adrienbrignon/mkdocs-exporter/commit/59e8fcf345c53a7c635d1614c12164244649b318))
* inserts newline between markdown and covers ([977c093](https://github.com/adrienbrignon/mkdocs-exporter/commit/977c0935c7374aa55395551f1052834637e28081))
* **pdf:** declare the books of pages with their documents ([ae4a0da](https://github.com/adrienbrignon/mkdocs-exporter/commit/ae4a0da11d9f08aa6886e178ed57879d55677da3))
* **pdf:** don't blame Chromium alone for combined documents that can't be measured ([fa1113b](https://github.com/adrienbrignon/mkdocs-exporter/commit/fa1113bd7d21286b5f684d1c6a1768307f0bfa73))
* **pdf:** give each page a part of its own with themes without content element ([a9f0d42](https://github.com/adrienbrignon/mkdocs-exporter/commit/a9f0d420eac1b697fd79d6d62cdb51289812c550))
* **pdf:** insert the parts of combined documents with BeautifulSoup 4.13.1 ([860ff47](https://github.com/adrienbrignon/mkdocs-exporter/commit/860ff47a35cd4838cabe61890b35a776b30066bc))
* **pdf:** keep em lengths of page rules unchanged ([40a03cb](https://github.com/adrienbrignon/mkdocs-exporter/commit/40a03cbb187ba93763df9777606c46dc01d94388))
* **pdf:** keep links to repeated anchors within their page in combined documents ([85b72a4](https://github.com/adrienbrignon/mkdocs-exporter/commit/85b72a4ba7fb0492dd3141409a688fa3817380d9))
* **pdf:** keep the text following {section} in headers and footers ([0f09b81](https://github.com/adrienbrignon/mkdocs-exporter/commit/0f09b8157192020aa4a151197f834660e988b122))
* **pdf:** lay out content on landscape pages with their width ([b136af7](https://github.com/adrienbrignon/mkdocs-exporter/commit/b136af7b9e5e56f179484b2cd1c00b53ad73b8dc))
* **pdf:** lay out the content's ancestors in the normal flow ([e595207](https://github.com/adrienbrignon/mkdocs-exporter/commit/e595207414c35a46961a43408b447db1a76d2cfd))
* **pdf:** leave headings that aren't printed out of combined documents' contents ([49c4b8b](https://github.com/adrienbrignon/mkdocs-exporter/commit/49c4b8b03d559023fc2b8ecd4a9ee1bb3f10fbc6))
* **pdf:** let styles teleported to the head take precedence over stylesheets ([563b3a5](https://github.com/adrienbrignon/mkdocs-exporter/commit/563b3a5e84ac441e70e7d1bd5b06e4875daab129))
* **pdf:** no book button on pages left out of books ([0731cf9](https://github.com/adrienbrignon/mkdocs-exporter/commit/0731cf946ab80d32f8c6e9daa7a1528b0e637d14))
* **pdf:** only leave the website's background out when pages have their own ([1abbb54](https://github.com/adrienbrignon/mkdocs-exporter/commit/1abbb54ff38e9358dde0aac421bc490f7fcf9943))
* **pdf:** start each build with a fresh browser context while serving ([8dbcecd](https://github.com/adrienbrignon/mkdocs-exporter/commit/8dbcecd6be7db2fc1450948cf57d67a3de53f23c))
* **pdf:** stop the website's background from hiding page backgrounds ([0ba7d35](https://github.com/adrienbrignon/mkdocs-exporter/commit/0ba7d356a6796313c0d4ce5782041b2116dce2a1))
* **pdf:** warn when a combined document is printed without being checked ([b52cca4](https://github.com/adrienbrignon/mkdocs-exporter/commit/b52cca4cb59526b083e48becf56e86f2d95cc008))


### Changed

* **covers:** compile cover templates once per build ([1ea30df](https://github.com/adrienbrignon/mkdocs-exporter/commit/1ea30df6644f4c5c6348543ba8a8047432f1e30d))
* **pdf:** assemble combined documents from the pages' prepared content ([15dd88d](https://github.com/adrienbrignon/mkdocs-exporter/commit/15dd88dce1883e8a67b3b95a6d3b0c804f8f342a))
* **pdf:** only render again the documents whose numbering changed ([bff4ca7](https://github.com/adrienbrignon/mkdocs-exporter/commit/bff4ca70bedf13a34cc3416816483ea096875990))
* **pdf:** release the content prepared for pages once books use it ([9eaebb2](https://github.com/adrienbrignon/mkdocs-exporter/commit/9eaebb277b8309bd56fcc6589a1d9ae03227c6e5))
* **pdf:** render at most 8 documents at once by default ([f77b2b7](https://github.com/adrienbrignon/mkdocs-exporter/commit/f77b2b7965ca2d7d5bf6e1d09c983c270a66c88f))
* **pdf:** render pages about a third faster ([6e54a99](https://github.com/adrienbrignon/mkdocs-exporter/commit/6e54a99ade6a84d53b58ecf80b628fcb7fb130ef))
* **pdf:** render twice as many documents at once as there are CPUs ([572d3e9](https://github.com/adrienbrignon/mkdocs-exporter/commit/572d3e9466e2c865ace8d403776095ed2429784b))
* rebuild the plugin on an engine-agnostic core ([31f584f](https://github.com/adrienbrignon/mkdocs-exporter/commit/31f584fcb04911f58ee8b9e29fa1a1cb2678c262)), closes [#33](https://github.com/adrienbrignon/mkdocs-exporter/issues/33) [#44](https://github.com/adrienbrignon/mkdocs-exporter/issues/44) [#45](https://github.com/adrienbrignon/mkdocs-exporter/issues/45) [#47](https://github.com/adrienbrignon/mkdocs-exporter/issues/47) [#48](https://github.com/adrienbrignon/mkdocs-exporter/issues/48) [#49](https://github.com/adrienbrignon/mkdocs-exporter/issues/49) [#51](https://github.com/adrienbrignon/mkdocs-exporter/issues/51) [#58](https://github.com/adrienbrignon/mkdocs-exporter/issues/58) [#60](https://github.com/adrienbrignon/mkdocs-exporter/issues/60) [#62](https://github.com/adrienbrignon/mkdocs-exporter/issues/62) [#65](https://github.com/adrienbrignon/mkdocs-exporter/issues/65) [#68](https://github.com/adrienbrignon/mkdocs-exporter/issues/68) [#73](https://github.com/adrienbrignon/mkdocs-exporter/issues/73) [#78](https://github.com/adrienbrignon/mkdocs-exporter/issues/78) [#85](https://github.com/adrienbrignon/mkdocs-exporter/issues/85) [#59](https://github.com/adrienbrignon/mkdocs-exporter/issues/59) [#63](https://github.com/adrienbrignon/mkdocs-exporter/issues/63) [#66](https://github.com/adrienbrignon/mkdocs-exporter/issues/66) [#69](https://github.com/adrienbrignon/mkdocs-exporter/issues/69) [#79](https://github.com/adrienbrignon/mkdocs-exporter/issues/79) [#81](https://github.com/adrienbrignon/mkdocs-exporter/issues/81)


### Chores

* release 7.0.0-rc.1 ([42b66b3](https://github.com/adrienbrignon/mkdocs-exporter/commit/42b66b33a0f5d4531958a2041ed8f33afe70e78c))

## [7.0.0] - Unreleased

Read the [migration guide](https://adrienbrignon.github.io/mkdocs-exporter/migration/v7/) when upgrading from v6.

### Added

- Combined documents have bookmarks following the navigation and the pages' headings (`outline`).
- Links between pages of combined documents point within the document (#52).
- Combined documents can have a table of contents with page numbers (`toc`) (#46).
- Documents of pages can start with a table of contents of their headings (`formats.pdf.toc`, or `toc` in a page's front matter) (#24).
- Several combined documents can be generated, selecting pages with patterns (`books`, `include`, `exclude`) (#31).
- Pages of combined documents can start on odd pages (`start: odd`) (#67).
- A ready-made button downloading the book a page is part of (`mkdocs_exporter.formats.pdf.buttons.book`).
- Headers and footers with placeholders (`header`, `footer`) (#84).
- Cover pages are Jinja templates, with or without the macros plugin (#50).
- Per-page documents have bookmarks and are tagged (accessibility).
- Unchanged documents are reused from a cache (`formats.pdf.cache`).
- `formats.pdf.serve` to generate documents while serving (the browser is kept open between rebuilds).
- `formats.pdf.browser.channel` and `formats.pdf.browser.delay` options (#81).
- `mkdocs-exporter-ignore` and `mkdocs-exporter-only` classes, for content of the website or of documents only (#33).
- `page-break`, `page-break-before` and `avoid-page-break` classes (#63).
- `MkDocsExporter.before` and `MkDocsExporter.after` hooks.
- Support for ProperDocs and for themes without dedicated support (#68).

### Changed

- Documents are printed by Chromium itself instead of the Paged.js polyfill: faster, with better CSS support (nesting, `@page` rules in media queries, different page sizes). Paged.js can still be loaded with `formats.pdf.scripts`.
- Requires Python 3.11+, MkDocs 1.6+ (#72) and Playwright 1.53+ (Chromium 138).
- Faster: pages are printed natively, about 2.4 times faster than with Paged.js (which was also inlined in every page), and opened as soon as they are loaded.
- Documents are rendered twice as many at a time as there are CPUs, up to 8, by default (`formats.pdf.concurrency`, 4 before).
- Combined documents are printed as a single document instead of rendering every page again and merging the documents: about 3 times faster on a 200-page website (3.4 s instead of 9.6 s), with page counters continuous in custom stylesheets too, identifiers of different pages kept apart (footnotes, tabs) and bookmarks pointing exactly at their headings.
- Pages are served to the browser by a local HTTP server: absolute paths, `srcset`, CSS `url()` and fetches resolve like on the website (#58, #62, #65).
- Pagination failures are reported immediately with the JavaScript error instead of timing out (#59, #79), and a failing page no longer prevents the others from being rendered.
- Documents are not generated by `mkdocs serve` by default (#78).
- Cover pages are no longer part of the website, nor processed as Markdown; the back cover comes after footnotes (#17).
- `formats.pdf.url` replaces the root of the website in links.
- The theme's scripts run in documents (e.g. Material's diagrams are rendered like on the website).
- The plugin no longer replaces the global asyncio event loop (#45, #47, #49).

### Fixed

- Download buttons link to the right document with `use_directory_urls: false` (#44, #60, #73).
- Page numbers of combined documents account for the actual size of removed covers (#66).
- Backgrounds of pages set by `@page` rules (e.g. a full-bleed cover's) are no longer hidden by the website's background, which is then left out of documents.
- Wide content and pages of different sizes no longer shrink every page of a document, with any theme; content printed on pages of another size (e.g. landscape pages for wide tables) is laid out with their width.
- Pages listed twice in the navigation, or skipped by dirty rebuilds, no longer break combined documents (#48, #51).
- Stylesheets excluded from the build are no longer rewritten (#85).
- `mailto:` and other non-HTTP links are preserved.
- The `metadata` of combined documents is honored.
- Scripts are injected even when no stylesheet is configured.
- The back cover is no longer broken when a page doesn't end with a blank line (#82).

### Deprecated

- `formats.pdf.aggregator`, replaced by `formats.pdf.books` (a list of combined documents).
- `data-decompose="true"`, replaced by the `mkdocs-exporter-only` class.

### Removed

- The bundled Paged.js (see the migration guide).
- Sass support: stylesheets must be plain CSS.
- The internal modules of v6 (see the migration guide).
