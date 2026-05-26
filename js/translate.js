(function() {
  var _cache = {};
  try { _cache = JSON.parse(localStorage.getItem('fp_trans') || '{}'); } catch(e) {}

  function ckey(text, to) { return to + '\x01' + text; }

  function saveCache() {
    try { localStorage.setItem('fp_trans', JSON.stringify(_cache)); } catch(e) {}
  }

  // Batch-translate array of strings, caches results
  async function batchTranslate(texts, to) {
    if (!texts || !texts.length) return [];
    var unique = [];
    var need = [];
    texts.forEach(function(t) {
      if (t && !_cache[ckey(t, to)] && unique.indexOf(t) === -1) {
        unique.push(t);
        need.push(t);
      }
    });

    if (need.length > 0) {
      // Split into chunks ≤1800 chars
      var chunks = [], curr = [], currLen = 0;
      need.forEach(function(text) {
        if (currLen + text.length > 1800 && curr.length) {
          chunks.push(curr.slice()); curr = []; currLen = 0;
        }
        curr.push(text); currLen += text.length + 3;
      });
      if (curr.length) chunks.push(curr);

      for (var ci = 0; ci < chunks.length; ci++) {
        var chunk = chunks[ci];
        var joined = chunk.join('\n||||\n'); // separator Google won't merge
        try {
          var url = 'https://translate.googleapis.com/translate_a/single?client=gtx&sl=uk&tl=' + to + '&dt=t&q=' + encodeURIComponent(joined);
          var resp = await fetch(url);
          var data = await resp.json();
          var full = data[0].map(function(x) { return x[0] || ''; }).join('');
          var parts = full.split(/\n\s*\|\|\|\|\s*\n/);
          chunk.forEach(function(orig, idx) {
            var tr = (parts[idx] || '').trim();
            _cache[ckey(orig, to)] = tr || orig;
          });
        } catch(e) {
          chunk.forEach(function(orig) { _cache[ckey(orig, to)] = orig; });
        }
      }
      saveCache();
    }

    return texts.map(function(t) { return (t && _cache[ckey(t, to)]) || t || ''; });
  }

  // Translate all product names (and cache them into nameEn)
  async function translateProducts(lang) {
    if (!lang || lang === 'ua' || !window.PRODUCTS || !window.PRODUCTS.length) return;
    var to = lang;

    var names = window.PRODUCTS.map(function(p) { return p.name || ''; });
    var translated = await batchTranslate(names, to);

    window.PRODUCTS.forEach(function(p, i) {
      if (!p.nameEn || p.nameEn === p.name) {
        p.nameEn = translated[i] || p.name;
      }
    });

    // Re-render
    if (typeof render === 'function') render();
    if (typeof renderCart === 'function') renderCart();
    if (typeof renderList === 'function') renderList();
    if (typeof window._renderRelated === 'function') window._renderRelated();

    // Also translate product detail page elements if on that page
    if (window._pdProduct) {
      translateProductDetail(window._pdProduct, window._pdCatLabel || '', lang);
    }
  }

  // Translate product detail page: name, category, breadcrumb, description, specs
  async function translateProductDetail(product, catLabel, lang) {
    if (!lang || lang === 'ua') return;
    var to = lang;
    var texts = [product.name || '', catLabel || '', product.description || ''].concat(product.details || []);
    var results = await batchTranslate(texts, to);

    var nameEl = document.querySelector('.pd-name');
    if (nameEl && results[0]) nameEl.textContent = results[0];

    var breadEl = document.getElementById('pdBreadcrumb');
    if (breadEl && results[0]) breadEl.textContent = results[0];

    var catEl = document.querySelector('.pd-category');
    if (catEl && results[1]) catEl.textContent = results[1];

    var descEl = document.getElementById('pdDesc');
    if (descEl && results[2]) descEl.textContent = results[2];

    var detailsEl = document.getElementById('pdDetails');
    if (detailsEl) {
      detailsEl.innerHTML = results.slice(3).map(function(d) {
        return '<li>' + d + '</li>';
      }).join('');
    }
  }

  // Expose globally
  window.autoTranslate    = batchTranslate;
  window.translateProducts = translateProducts;
  window.translateProductDetail = translateProductDetail;

  // Auto-run on page load if already in EN mode
  if (typeof onProductsReady === 'function') {
    onProductsReady(function() {
      if (window.LANG && window.LANG !== 'ua') {
        translateProducts(window.LANG);
      }
    });
  }
})();
