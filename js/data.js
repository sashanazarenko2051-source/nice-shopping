var PRODUCTS = [];

// Load products from localStorage (set by admin panel)
(function() {
  try {
    var stored = localStorage.getItem('ns_products');
    if (stored) {
      var parsed = JSON.parse(stored);
      if (Array.isArray(parsed) && parsed.length > 0) PRODUCTS = parsed;
    }
  } catch(e) {}
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
