var PRODUCTS = [];
var _pReady = false;
var _pCbs = [];

function onProductsReady(cb) {
  if (_pReady) { cb(); } else { _pCbs.push(cb); }
}

(function() {
  fetch('/api/products')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      PRODUCTS = Array.isArray(data) ? data : [];
    })
    .catch(function() {})
    .finally(function() {
      _pReady = true;
      _pCbs.forEach(function(cb) { try { cb(); } catch(e) {} });
      _pCbs = [];
    });
})();

