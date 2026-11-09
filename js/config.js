// Копия сайта на GitHub Pages (или открытый с диска файл) работает без сервера:
// запросы /api/... отправляем на основной сайт, чтобы были товары, отзывы и заказы.
(function () {
  if (location.protocol !== 'file:' && !/github\.io$/.test(location.hostname)) return;
  var BASE = 'https://nice-shopping.onrender.com', f = window.fetch.bind(window);
  window.fetch = function (u, o) { if (typeof u === 'string' && u.indexOf('/api/') === 0) u = BASE + u; return f(u, o); };
})();

const CONFIG = {
  storeName: 'Файні покупки',
  currency: '₴',
  phone: '+380954141820',
  phoneName: 'Тетяна',
  email: 'ornazartatyana@gmail.com',
  telegram: 'NazarT85',
  instagram: 'fayni_pokupky',
  telegramBotToken: '',
  telegramChatId: '',
};
