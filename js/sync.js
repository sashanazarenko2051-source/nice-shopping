(function() {
  var BASE = 'https://api.jsonbin.io/v3/b';

  function masterKey() {
    return (typeof CONFIG !== 'undefined' && CONFIG.jsonbinKey) || localStorage.getItem('ns_jb_key') || '';
  }
  function productsBinId() {
    return (typeof CONFIG !== 'undefined' && CONFIG.jsonbinProductsBin) || localStorage.getItem('ns_jb_pb') || '';
  }
  function ordersBinId() {
    return (typeof CONFIG !== 'undefined' && CONFIG.jsonbinOrdersBin) || localStorage.getItem('ns_jb_ob') || '';
  }

  async function jbGet(binId) {
    var headers = {};
    var key = masterKey();
    if (key) headers['X-Master-Key'] = key;
    var r = await fetch(BASE + '/' + binId + '/latest', { headers: headers });
    if (!r.ok) throw new Error(r.status);
    var d = await r.json();
    return d.record;
  }

  async function jbPut(binId, data) {
    var r = await fetch(BASE + '/' + binId, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Master-Key': masterKey() },
      body: JSON.stringify(data)
    });
    if (!r.ok) throw new Error(r.status);
  }

  async function jbCreate(name, data, pub) {
    var h = { 'Content-Type': 'application/json', 'X-Master-Key': masterKey(), 'X-Bin-Name': name };
    if (!pub) h['X-Bin-Private'] = 'true';
    var r = await fetch(BASE, { method: 'POST', headers: h, body: JSON.stringify(data) });
    if (!r.ok) throw new Error(r.status);
    var d = await r.json();
    return d.metadata.id;
  }

  window.syncCloud = {
    hasKey: function() { return !!masterKey(); },
    hasBin: function() { return !!productsBinId(); },
    productsBinId: productsBinId,
    ordersBinId: ordersBinId,

    loadProducts: async function() {
      var bid = productsBinId();
      if (!bid) return false;
      try {
        var products = await jbGet(bid);
        if (Array.isArray(products)) {
          localStorage.setItem('ns_products', JSON.stringify(products));
          if (window.PRODUCTS) {
            PRODUCTS.length = 0;
            products.forEach(function(p) { PRODUCTS.push(p); });
          }
          return true;
        }
      } catch(e) { console.warn('Cloud load products:', e.message); }
      return false;
    },

    saveProducts: async function(products) {
      if (!masterKey()) return false;
      var bid = productsBinId();
      try {
        if (!bid) {
          bid = await jbCreate('nice-products', products, true);
          localStorage.setItem('ns_jb_pb', bid);
        } else {
          await jbPut(bid, products);
        }
        return bid;
      } catch(e) { console.warn('Cloud save products:', e.message); return false; }
    },

    loadOrders: async function() {
      if (!masterKey()) return false;
      var bid = ordersBinId();
      if (!bid) return false;
      try {
        var orders = await jbGet(bid);
        if (Array.isArray(orders)) {
          localStorage.setItem('ns_orders', JSON.stringify(orders));
          return true;
        }
      } catch(e) { console.warn('Cloud load orders:', e.message); }
      return false;
    },

    saveOrders: async function(orders) {
      if (!masterKey()) return false;
      var bid = ordersBinId();
      try {
        if (!bid) {
          bid = await jbCreate('nice-orders', orders, false);
          localStorage.setItem('ns_jb_ob', bid);
        } else {
          await jbPut(bid, orders);
        }
        return true;
      } catch(e) { console.warn('Cloud save orders:', e.message); return false; }
    },

    setup: async function(key) {
      if (key) localStorage.setItem('ns_jb_key', key);
      var pb = productsBinId();
      var ob = ordersBinId();
      try {
        if (!pb) {
          var products = [];
          try { products = JSON.parse(localStorage.getItem('ns_products')) || []; } catch(e) {}
          pb = await jbCreate('nice-products', products, true);
          localStorage.setItem('ns_jb_pb', pb);
        }
        if (!ob) {
          var orders = [];
          try { orders = JSON.parse(localStorage.getItem('ns_orders')) || []; } catch(e) {}
          ob = await jbCreate('nice-orders', orders, false);
          localStorage.setItem('ns_jb_ob', ob);
        }
        return { ok: true, pb: pb, ob: ob };
      } catch(e) { return { ok: false, error: e.message }; }
    }
  };
})();
