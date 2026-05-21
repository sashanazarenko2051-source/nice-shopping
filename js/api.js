var API = (function() {
  var _token = localStorage.getItem('ns_admin_token') || '';

  function _headers() {
    var h = { 'Content-Type': 'application/json' };
    if (_token) h['Authorization'] = 'Bearer ' + _token;
    return h;
  }

  function _req(url, opts) {
    return fetch(url, opts).then(function(r) {
      if (!r.ok) return r.json().then(function(e) { throw new Error(e.detail || r.status); });
      return r.json();
    });
  }

  return {
    setToken: function(t) { _token = t; localStorage.setItem('ns_admin_token', t); },
    clearToken: function() { _token = ''; localStorage.removeItem('ns_admin_token'); },
    hasToken: function() { return !!_token; },

    login: function(pass) {
      return _req('/api/admin/login', { method: 'POST', headers: _headers(), body: JSON.stringify({ password: pass }) });
    },

    getProducts: function() { return _req('/api/products', { headers: _headers() }); },
    saveAllProducts: function(list) {
      return _req('/api/products', { method: 'PUT', headers: _headers(), body: JSON.stringify(list) });
    },
    addProduct: function(data) {
      return _req('/api/products/one', { method: 'POST', headers: _headers(), body: JSON.stringify(data) });
    },
    updateProduct: function(id, data) {
      return _req('/api/products/' + id, { method: 'PUT', headers: _headers(), body: JSON.stringify(data) });
    },
    deleteProduct: function(id) {
      return _req('/api/products/' + id, { method: 'DELETE', headers: _headers() });
    },

    getOrders: function() { return _req('/api/orders', { headers: _headers() }); },
    createOrder: function(data) {
      return _req('/api/orders', { method: 'POST', headers: _headers(), body: JSON.stringify(data) });
    },
    deleteOrder: function(id) {
      return _req('/api/orders/' + id, { method: 'DELETE', headers: _headers() });
    },

    getReviews: function() { return _req('/api/reviews', { headers: _headers() }); },
    createReview: function(data) {
      return _req('/api/reviews', { method: 'POST', headers: _headers(), body: JSON.stringify(data) });
    },
  };
})();
