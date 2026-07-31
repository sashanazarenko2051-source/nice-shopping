var PRODUCTS = [];
var _pReady = false;
var _pCbs = [];

function onProductsReady(cb) {
  if (_pReady) { cb(); } else { _pCbs.push(cb); }
}

(function() {
  var delays = [0, 4000, 8000]; // retry after 4s and 8s (helps with Render cold start)
  var attempt = 0;

  function load() {
    fetch('/api/products')
      .then(function(r) {
        if (!r.ok) throw new Error(r.status);
        return r.json();
      })
      .then(function(data) {
        PRODUCTS = Array.isArray(data) ? data : [];
        _pReady = true;
        _pCbs.forEach(function(cb) { try { cb(); } catch(e) {} });
        _pCbs = [];
      })
      .catch(function() {
        attempt++;
        if (attempt < delays.length) {
          setTimeout(load, delays[attempt]);
        } else {
          _pReady = true;
          _pCbs.forEach(function(cb) { try { cb(); } catch(e) {} });
          _pCbs = [];
        }
      });
  }
  load();
})();
