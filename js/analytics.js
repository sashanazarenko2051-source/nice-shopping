// Track page visit (called automatically on every page load)
(function() {
  var today = new Date().toISOString().split('T')[0];
  var visits = {};
  try { visits = JSON.parse(localStorage.getItem('ns_visits')) || {}; } catch(e) {}
  visits[today] = (visits[today] || 0) + 1;
  localStorage.setItem('ns_visits', JSON.stringify(visits));
})();
