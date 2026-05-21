function getCart() {
  return JSON.parse(localStorage.getItem('fp_cart') || '[]');
}

function saveCart(cart) {
  localStorage.setItem('fp_cart', JSON.stringify(cart));
  updateCartCount();
}

function addToCart(productId, size, qty) {
  qty = qty || 1;
  var cart = getCart();
  var product = PRODUCTS.find(function(p) { return p.id === productId; });
  if (!product) return;
  var key = productId + '-' + size;
  var existing = cart.find(function(i) { return i.key === key; });
  if (existing) { existing.qty += qty; }
  else { cart.push({ key: key, productId: productId, size: size, qty: qty }); }
  saveCart(cart);
  showToast('"' + product.name + '" додано до кошика');
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

function renderProductCard(product) {
  var discount = product.oldPrice ? Math.round((1 - product.price / product.oldPrice) * 100) : null;
  var fullStars = Math.round(product.rating);
  var stars = '★'.repeat(fullStars) + '☆'.repeat(5 - fullStars);
  var imgHtml = product.img
    ? '<img src="' + product.img + '" alt="' + product.name + '" loading="lazy" onerror="this.style.background=\'linear-gradient(135deg,#f0e8e8,#e0d0d0)\';this.style.minHeight=\'100%\';this.src=\'\'">'
    : '<div style="width:100%;height:100%;background:linear-gradient(135deg,#f0e8e8,#e0d0d0)"></div>';
  return '<div class="product-card">' +
    '<div class="product-card__img-wrap">' +
      '<a href="product.html?id=' + product.id + '">' + imgHtml + '</a>' +
      (discount ? '<span class="badge-sale">-' + discount + '%</span>' : '') +
      '<div class="product-card__quick" onclick="quickAdd(' + product.id + ')">Швидко додати</div>' +
    '</div>' +
    '<div class="product-card__name"><a href="product.html?id=' + product.id + '">' + product.name + '</a></div>' +
    '<div class="product-card__prices">' +
      '<span class="price">' + CONFIG.currency + product.price + '</span>' +
      (product.oldPrice ? '<span class="price-old">' + CONFIG.currency + product.oldPrice + '</span>' : '') +
    '</div>' +
    '<div class="product-card__rating"><span class="stars">' + stars + '</span><span class="reviews">(' + product.reviews + ')</span></div>' +
    (product.stock != null ? '<div class="product-card__stock' + (product.stock === 0 ? ' out' : '') + '">' + (product.stock === 0 ? '❌ Немає в наявності' : '✅ В наявності: ' + product.stock + ' шт.') + '</div>' : '') +
  '</div>';
}

function quickAdd(productId) {
  var product = PRODUCTS.find(function(p) { return p.id === productId; });
  if (product) addToCart(productId, product.sizes[0]);
}

document.addEventListener('DOMContentLoaded', function() {
  updateCartCount();
  var toggle = document.getElementById('menuToggle');
  var nav = document.querySelector('.nav');
  if (toggle && nav) {
    toggle.addEventListener('click', function() { nav.classList.toggle('open'); });
  }
});
