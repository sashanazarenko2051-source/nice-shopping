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

var NAV_CATEGORIES = [
  { key:'socks',    gender:'women', label:'👩 Жіночі шкарпетки' },
  { key:'socks',    gender:'men',   label:'👨 Чоловічі шкарпетки' },
  { key:'lingerie', gender:'women', label:'👩 Жіноча нижня білизна' },
  { key:'lingerie', gender:'men',   label:'👨 Чоловіча нижня білизна' },
  { key:'bras',     gender:'women', label:'✨ Бюстгальтери' },
];

function catUrl(key, gender) {
  return 'catalog.html?cat=' + key + (gender ? '&gender=' + gender : '');
}
