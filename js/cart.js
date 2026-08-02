function getCart() {
  return JSON.parse(localStorage.getItem('fp_cart') || '[]');
}

function saveCart(cart) {
  localStorage.setItem('fp_cart', JSON.stringify(cart));
  updateCartCount();
}

function addToCart(productId, size, qty, color) {
  qty = qty || 1;
  var cart = getCart();
  var product = PRODUCTS.find(function(p) { return p.id === productId; });
  if (!product) return;
  var key = productId + '-' + size + (color ? '-' + color : '');
  var existing = cart.find(function(i) { return i.key === key; });
  if (existing) { existing.qty += qty; }
  else { cart.push({ key: key, productId: productId, size: size, qty: qty, color: color || '' }); }
  saveCart(cart);
  showToast('"' + product.name + '" ' + window.i18n('cart.added'));
}

function removeFromCart(key) {
  saveCart(getCart().filter(function(i) { return i.key !== key; }));
}

function updateQty(key, qty) {
  var cart = getCart();
  var item = cart.find(function(i) { return i.key === key; });
  if (!item) return;
  if (qty <= 0) { removeFromCart(key); return; }
  item.qty = qty;
  saveCart(cart);
}

function clearCart() {
  localStorage.removeItem('fp_cart');
  updateCartCount();
}

function getCartTotal() {
  return getCart().reduce(function(total, item) {
    var p = PRODUCTS.find(function(x) { return x.id === item.productId; });
    return total + (p ? p.price * item.qty : 0);
  }, 0);
}

function getCartItemCount() {
  return getCart().reduce(function(sum, item) { return sum + item.qty; }, 0);
}

function updateCartCount() {
  var count = getCartItemCount();
  document.querySelectorAll('.cart-count').forEach(function(el) {
    el.textContent = count;
    el.style.display = count === 0 ? 'none' : 'flex';
  });
}

function showToast(message, type) {
  var toast = document.getElementById('toast');
  if (!toast) return;
  toast.textContent = message;
  toast.className = 'toast show' + (type ? ' toast--' + type : '');
  clearTimeout(toast._t);
  toast._t = setTimeout(function() { toast.className = 'toast'; }, 3000);
}

var _cardColors = {};

function getWishlist() {
  try { return JSON.parse(localStorage.getItem('ns_wishlist')) || []; } catch(e) { return []; }
}
function toggleWishlist(pid, el) {
  var list = getWishlist();
  var idx = list.indexOf(pid);
  if (idx === -1) { list.push(pid); el.classList.add('active'); el.textContent = '♥'; el.title = 'В вибраних'; }
  else { list.splice(idx, 1); el.classList.remove('active'); el.textContent = '♡'; el.title = 'Додати до вибраних'; }
  localStorage.setItem('ns_wishlist', JSON.stringify(list));
}

function renderProductCard(product) {
  var isOos = product.stock != null && product.stock === 0;
  var liked = getWishlist().indexOf(product.id) !== -1;
  var discount = product.oldPrice ? Math.round((1 - product.price / product.oldPrice) * 100) : null;
  var fullStars = Math.round(product.rating);
  var stars = '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
  var imgSrc = product.imageUrl || product.img || '';
  var displayName = (window.LANG === 'en' && product.nameEn) ? product.nameEn : product.name;
  var isData = imgSrc && imgSrc.indexOf('data:') === 0;
  var imgHtml = imgSrc
    ? '<img src="' + imgSrc + '" alt="' + displayName + '"' + (isData ? '' : ' loading="lazy"') + ' onerror="this.onerror=null;this.style.display=\'none\'">'
    : '<div style="width:100%;height:100%;background:linear-gradient(135deg,var(--card2),var(--card))"></div>';
  var quickLabel = (window.i18n && window.i18n('quick.add')) || 'Швидко додати';

  var colorsHtml = '';
  if (product.colors && product.colors.length > 1) {
    var selectedColor = _cardColors[product.id] || product.colors[0].name;
    colorsHtml = '<div class="card-colors">' +
      product.colors.map(function(c) {
        var isActive = c.name === selectedColor;
        return '<div class="card-swatch' + (isActive ? ' active' : '') + '" style="background:' + c.hex + '" data-pid="' + product.id + '" data-color="' + c.name.replace(/"/g,'&quot;') + '" title="' + c.name.replace(/"/g,'&quot;') + '" onclick="selectCardColor(this)"></div>';
      }).join('') +
    '</div>';
  }

  var productUrl = 'product.html?id=' + product.id;
  var selColor = _cardColors[product.id] || (product.colors && product.colors.length ? product.colors[0].name : '');
  if (selColor) productUrl += '&color=' + encodeURIComponent(selColor);

  var wishBtn = '<button class="wishlist-btn' + (liked ? ' active' : '') + '" onclick="event.preventDefault();toggleWishlist(' + product.id + ',this)" title="' + (liked ? 'В вибраних' : 'Додати до вибраних') + '" aria-label="wishlist">' + (liked ? '♥' : '♡') + '</button>';

  var stockHtml = '';
  if (product.stock != null) {
    var s = product.stock;
    var cls = s === 0 ? ' out' : s <= 3 ? ' limited' : '';
    var lbl = s === 0 ? '❌ Немає в наявності' : s <= 3 ? '⚡ Обмежена кількість' : '✓ В наявності';
    stockHtml = '<div class="product-card__stock' + cls + '">' + lbl + '</div>';
  }

  var ratingRow = '<div class="product-card__rating">' +
    '<span class="stars">' + stars + '</span>' +
    (product.reviews ? '<span class="reviews">' + product.reviews + ' відг.</span>' : '') +
    '</div>';

  var priceRow = '<div class="product-card__prices">' +
    '<span class="price">' + CONFIG.currency + product.price + '</span>' +
    (product.oldPrice ? '<span class="price-old">' + CONFIG.currency + product.oldPrice + '</span>' : '') +
    (discount ? '<span class="badge-sale-inline">-' + discount + '%</span>' : '') +
    '</div>';

  var bottomAction = isOos
    ? '<button class="oos-notify" onclick="showToast(\'🔔 Ми сповістимо вас як тільки товар з\'явиться!\')">🔔 Сповістити про наявність</button>'
    : '';

  return '<div class="product-card' + (isOos ? ' product-card--oos' : '') + '">' +
    '<div class="product-card__img-wrap">' +
      wishBtn +
      '<a href="' + productUrl + '">' + imgHtml + '</a>' +
      (discount ? '<span class="badge-sale">−' + discount + '%</span>' : '') +
      '<button class="product-card__quick" onclick="quickAdd(' + product.id + ')" style="' + (isOos ? 'display:none' : '') + '">' +
        '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" style="vertical-align:middle;margin-right:5px"><path d="M6 2L3 6v14a2 2 0 002 2h14a2 2 0 002-2V6l-3-4z"/><line x1="3" y1="6" x2="21" y2="6"/><path d="M16 10a4 4 0 01-8 0"/></svg>' +
        quickLabel +
      '</button>' +
    '</div>' +
    '<div class="product-card__body">' +
      '<div class="product-card__name"><a href="' + productUrl + '">' + displayName + '</a></div>' +
      colorsHtml +
      priceRow +
      ratingRow +
      stockHtml +
    '</div>' +
    bottomAction +
  '</div>';
}

function selectCardColor(el) {
  var pid = parseInt(el.dataset.pid);
  var colorName = el.dataset.color;
  _cardColors[pid] = colorName;
  // Update swatch active state
  var siblings = el.parentNode.querySelectorAll('.card-swatch');
  siblings.forEach(function(s) { s.classList.remove('active'); });
  el.classList.add('active');
  // Update card links to pass selected color
  var card = el.closest('.product-card');
  if (card) {
    var url = 'product.html?id=' + pid + '&color=' + encodeURIComponent(colorName);
    card.querySelectorAll('a[href*="product.html"]').forEach(function(a) { a.href = url; });
  }
}

function quickAdd(productId) {
  var product = PRODUCTS.find(function(p) { return p.id === productId; });
  if (!product || !product.sizes || !product.sizes.length) return;
  var color = _cardColors[productId] || (product.colors && product.colors.length ? product.colors[0].name : '');
  addToCart(productId, product.sizes[0], 1, color);
}

document.addEventListener('DOMContentLoaded', function() {
  updateCartCount();
  // NOTE: the mobile menu toggle is bound per-page (inline). Do NOT bind it here
  // as well — a double binding makes each tap fire twice and the menu never opens.
});
