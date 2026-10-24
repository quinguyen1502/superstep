// Renders the public OpenAPI spec with the vendored Redoc bundle (javascripts/vendor/redoc.standalone.js, v2.5.4,
// MIT) into <div id="api-reference" data-spec="..."> on the API reference pages. Everything is served by the handbook
// itself, so the page works offline. The spec is a copy of docs/api/openapi.public.json (scripts/gen_public_openapi.py).
(function () {
  function render() {
    var el = document.getElementById('api-reference')
    if (!el || !window.Redoc || el.dataset.rendered) return
    el.dataset.rendered = '1'
    var css = getComputedStyle(document.body)
    var primary = css.getPropertyValue('--md-primary-fg-color').trim() || '#4f46e5'
    var header = document.querySelector('.md-header')
    window.Redoc.init(new URL(el.dataset.spec, document.baseURI).href, {
      hideDownloadButton: false,
      expandResponses: '200,202',
      nativeScrollbars: true,
      requiredPropsFirst: true,
      sortPropsAlphabetically: false,
      scrollYOffset: header ? header.offsetHeight : 0,
      theme: { colors: { primary: { main: primary } }, typography: { fontFamily: 'inherit', headings: { fontFamily: 'inherit' } } },
    }, el)
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', render)
  else render()
})()
