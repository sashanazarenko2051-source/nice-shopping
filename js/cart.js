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

function renderProductCard(product) {
  var discount = product.oldPrice ? Math.round((1 - product.price / product.oldPrice) * 100) : null;
  var fullStars = Math.round(product.rating);
  var stars = '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
  var imgSrc = product.imageUrl || product.img || '';
  var displayName = (window.LANG === 'en' && product.nameEn) ? product.nameEn : product.name;
  var isData = imgSrc && imgSrc.indexOf('data:') === 0;
  var imgHtml = imgSrc
    ? '<img src="' + imgSrc + '" alt="' + displayName + '"' + (isData ? '' : ' loading="lazy"') + ' onerror="this.onerror=null;this.style.display=\'none\'">'
    : '<div style="width:100%;height:100%;background:linear-gradient(135deg,#f0e8e8,#e0d0d0)"></div>';
  var quickLabel = (window.i18n && window.i18n('quick.add')) || 'Швидко додати';

  // Color swatches for catalog cards
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

  return '<div class="product-card">' +
    '<div class="product-card__img-wrap">' +
      '<a href="' + productUrl + '">' + imgHtml + '</a>' +
      (discount ? '<span class="badge-sale">-' + discount + '%</span>' : '') +
      '<div class="product-card__quick" onclick="quickAdd(' + product.id + ')">' + quickLabel + '</div>' +
    '</div>' +
    '<div class="product-card__name"><a href="' + productUrl + '">' + displayName + '</a></div>' +
    colorsHtml +
    '<div class="product-card__prices">' +
      '<span class="price">' + CONFIG.currency + product.price + '</span>' +
      (product.oldPrice ? '<span class="price-old">' + CONFIG.currency + product.oldPrice + '</span>' : '') +
    '</div>' +
    '<div class="product-card__rating"><span class="stars">' + stars + '</span><span class="reviews">(' + product.reviews + ')</span></div>' +
    (product.stock != null ? '<div class="product-card__stock' + (product.stock === 0 ? ' out' : '') + '">' + (product.stock === 0 ? '❌ ' + (window.LANG==='en'?'Out of stock':'Немає в наявності') : '✅ ' + (window.LANG==='en'?'In stock':'В наявності') + ': ' + product.stock + ' ' + (window.LANG==='en'?'pcs.':'шт.')) + '</div>' : '') +
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
  var toggle = document.getElementById('menuToggle');
  var nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function() { nav.classList.toggle('open'); });
  }
});
