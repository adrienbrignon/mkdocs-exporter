window.MathJax = {
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']],
    processEscapes: true,
    processEnvironments: true
  },
  options: {
    enableMenu: false,
    ignoreHtmlClass: '.*|',
    enableEnrichment: false,
    processHtmlClass: 'arithmatex',
    menuOptions: {
      settings: {
        enrich: false,
        collapsible: false,
        speech: false,
        braille: false,
        assistiveMml: false,
      }
    },
  }
};

document$.subscribe(() => {
  MathJax.typesetPromise();
});
