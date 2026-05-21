(function() {
  var LANG = localStorage.getItem('fp_lang') || 'ua';

  var T = {
    ua: {
      logo: 'Файні покупки',
      'nav.catalog': 'Каталог', 'nav.contacts': 'Контакти',
      'nav.home': 'Головна', 'nav.cart': 'Кошик', 'nav.reviews': 'Відгуки',
      'hero.h1': 'Ваш комфорт —<br><em>наш стиль</em>',
      'hero.p': 'Нижня білизна та шкарпетки преміум-якості. Для тих, хто цінує якість і зручність щодня.',
      'hero.btn1': 'Перейти до каталогу', 'hero.btn2': "Зв'язатись з нами",
      'hero.badge': '✨ Колекція 2025',
      'hero.products': 'товарів', 'hero.sections': 'розділів', 'hero.quality': 'якість',
      'hero.np': 'Нова Пошта', 'hero.up': 'Укрпошта', 'hero.delivery.sub': 'Доставка по Україні',
      'hero.rating.sub': 'Рейтинг магазину',
      'trust.delivery': '🚚 Доставка по всій Україні', 'trust.quality': '💎 Преміум якість',
      'trust.payment': '💳 Накладений платіж', 'trust.service': '📞 Особистий підхід',
      'cta.title': "Зв'язатись з нами", 'cta.sub': 'Напишіть нам — підберемо ідеальний варіант разом',
      'cta.btn': 'Написати у Telegram →',
      'cat.go': 'Переглянути →',
      'slabel.assort': 'АСОРТИМЕНТ', 'slabel.why': 'ПЕРЕВАГИ', 'slabel.process': 'ПРОЦЕС',
      'why.title': 'Чому обирають нас',
      'why.1t': 'Швидка доставка', 'why.1p': 'Відправляємо Новою Поштою та Укрпоштою. Замовлення сьогодні — у вас завтра.',
      'why.2t': 'Висока якість', 'why.2p': 'Тільки перевірені матеріали та виробники. Кожен товар проходить контроль якості.',
      'why.3t': 'Особистий підхід', 'why.3p': "Тетяна завжди на зв'язку та допоможе підібрати ідеальний варіант саме для вас.",
      'cats.title': 'Наші категорії',
      'cat.ws': 'Жіночі шкарпетки', 'cat.ms': 'Чоловічі шкарпетки',
      'cat.wl': 'Жіноча нижня білизна', 'cat.ml': 'Чоловіча нижня білизна', 'cat.br': 'Бюстгальтери',
      'how.title': 'Як зробити замовлення?',
      'how.s1t': 'Оберіть товар', 'how.s1p': 'Перегляньте каталог та оберіть товари, які вас зацікавили',
      'how.s2t': "Зв'яжіться з нами", 'how.s2p': 'Напишіть у Telegram @NazarT84 або зателефонуйте Тетяні',
      'how.s3t': 'Отримайте замовлення', 'how.s3p': 'Відправляємо Новою Поштою та Укрпоштою по всій Україні',
      'footer.nav': 'Навігація', 'footer.cats': 'Категорії',
      'footer.desc': 'Якісна нижня білизна та шкарпетки для жінок і чоловіків. Зручно, красиво, доступно.',
      'footer.rights': 'Усі права захищені', 'footer.copy': '© 2025 Nice Shopping',
      'footer.wl': 'Жіноча білизна', 'footer.ml': 'Чоловіча білизна',
      'bc.home': 'Головна', 'bc.catalog': 'Каталог', 'bc.contacts': 'Контакти',
      'bc.cart': 'Кошик', 'bc.checkout': 'Оформлення', 'bc.reviews': 'Відгуки',
      'page.catalog': 'Каталог', 'page.contacts': 'Контакти',
      'page.cart': 'Кошик', 'page.checkout': 'Оформлення замовлення', 'page.reviews': 'Відгуки',
      'filter.cat': 'Категорія', 'filter.all': 'Всі',
      'filter.ws': 'Жіночі шкарпетки', 'filter.ms': 'Чоловічі шкарпетки',
      'filter.wl': 'Жіноча нижня білизна', 'filter.ml': 'Чоловіча нижня білизна', 'filter.br': 'Бюстгальтери',
      'filter.wws': 'Жіночі зимові шкарпетки', 'filter.wms': 'Чоловічі зимові шкарпетки',
      'filter.sws': 'Жіночі літні шкарпетки', 'filter.sms': 'Чоловічі літні шкарпетки',
      'filter.size': 'Розмір',
      'stock.in': 'В наявності', 'stock.out': 'Немає в наявності', 'stock.pcs': 'шт.',
      'sort.default': 'Сортування', 'sort.asc': 'Ціна: від дешевих', 'sort.desc': 'Ціна: від дорогих',
      'sort.rating': 'За рейтингом', 'sort.discount': 'Зі знижкою',
      'info.phone': 'Телефон', 'info.phone_v': '+380 95 414 18 20 — Тетяна',
      'info.delivery': 'Доставка', 'info.delivery_v': 'Нова Пошта та Укрпошта',
      'info.hours': 'Час роботи', 'info.hours_v': 'Пн–Нд: 9:00 — 21:00',
      'card.tg.t': 'Telegram', 'card.tg.p': "Найшвидший спосіб зв'язатись. Відповімо протягом кількох хвилин.", 'card.tg.btn': 'Написати',
      'card.ph.t': 'Телефон', 'card.ph.p': "Тетяна завжди на зв'язку і рада допомогти з вибором.", 'card.ph.btn': 'Зателефонувати',
      'form.title': 'Надіслати повідомлення',
      'form.nl': "Ваше ім'я *", 'form.pl': 'Телефон *', 'form.ml': 'Повідомлення *',
      'form.np': 'Олена', 'form.pp': '+380 XX XXX XX XX', 'form.mp': 'Ваше питання або запит...',
      'form.sub': 'Надіслати →', 'form.ok.t': 'Повідомлення надіслано!', 'form.ok.p': "Ми зв'яжемось з вами найближчим часом.",
      'rev.form.title': 'Залишити відгук',
      'rev.form.sub': 'Поділіться своїми враженнями від покупки — це допоможе іншим покупцям',
      'rev.form.name': "Ваше ім'я *", 'rev.form.name.ph': 'Олена',
      'rev.form.rating': 'Оцінка *', 'rev.form.text': 'Відгук *',
      'rev.form.text.ph': 'Розкажіть про ваш досвід покупки...',
      'rev.form.btn': 'Опублікувати відгук →', 'rev.sending': 'Публікуємо...',
      'rev.ok.t': 'Дякуємо за відгук!', 'rev.ok.p': 'Ваш відгук опубліковано. Це дуже важливо для нас!',
      'rev.ok.btn': 'Написати ще один →',
      'rev.list.title': 'Відгуки покупців',
      'rev.empty': 'Поки немає відгуків.<br>Будьте першим!',
      'cart.empty.t': 'Кошик порожній', 'cart.empty.p': 'Додайте товари, які вам сподобались', 'cart.empty.btn': 'До каталогу',
      'cart.cont': '← Продовжити покупки', 'cart.summ': 'Підсумок замовлення',
      'cart.del': 'Доставка', 'cart.total': 'Разом', 'cart.free': '✓ Безкоштовна доставка',
      'cart.chk': 'Оформити замовлення', 'cart.size': 'Розмір', 'cart.items': 'Товари',
      'cart.still': 'Ще', 'cart.til': 'до безкоштовної доставки',
      'co.contact': 'Контактні дані', 'co.first': "Ім'я *", 'co.last': 'Прізвище *',
      'co.phone': 'Телефон *', 'co.email': 'Email',
      'co.del': 'Доставка (Нова Пошта / Укрпошта)',
      'co.city': 'Місто *', 'co.branch': 'Відділення або адреса доставки *',
      'co.comment': 'Коментар до замовлення', 'co.payment': 'Оплата',
      'co.cod': '💵 Накладений платіж', 'co.cod_d': 'Оплата при отриманні + комісія пошти',
      'co.prepay': '💳 Передоплата на картку', 'co.prepay_d': 'Реквізити надішлемо після підтвердження',
      'co.sub': 'Оформити замовлення →', 'co.agree': 'Натискаючи кнопку, ви погоджуєтеся з умовами магазину',
      'co.order': 'Ваше замовлення', 'co.sending': 'Відправляємо...',
      'co.ok.t': 'Замовлення прийнято!', 'co.ok.p': "Дякуємо за покупку! Ми зв'яжемось з вами найближчим часом.", 'co.ok.btn': 'Продовжити покупки',
    },
    en: {
      logo: 'Nice Shopping',
      'nav.catalog': 'Catalog', 'nav.contacts': 'Contacts',
      'nav.home': 'Home', 'nav.cart': 'Cart', 'nav.reviews': 'Reviews',
      'hero.h1': 'Your comfort —<br><em>our style</em>',
      'hero.p': 'Premium-quality underwear and socks. For those who value quality and comfort every day.',
      'hero.btn1': 'Go to catalog', 'hero.btn2': 'Contact us',
      'hero.badge': '✨ Collection 2025',
      'hero.products': 'items', 'hero.sections': 'sections', 'hero.quality': 'quality',
      'hero.np': 'Nova Poshta', 'hero.up': 'Ukrposhta', 'hero.delivery.sub': 'Delivery across Ukraine',
      'hero.rating.sub': 'Store rating',
      'trust.delivery': '🚚 Delivery across Ukraine', 'trust.quality': '💎 Premium quality',
      'trust.payment': '💳 Cash on delivery', 'trust.service': '📞 Personal approach',
      'cta.title': 'Contact us', 'cta.sub': "Write to us — we'll find the perfect option together",
      'cta.btn': 'Message us on Telegram →',
      'cat.go': 'View →',
      'slabel.assort': 'ASSORTMENT', 'slabel.why': 'BENEFITS', 'slabel.process': 'PROCESS',
      'why.title': 'Why choose us',
      'why.1t': 'Fast delivery', 'why.1p': 'We ship via Nova Poshta & Ukrposhta. Order today — get it tomorrow.',
      'why.2t': 'Premium quality', 'why.2p': 'Only verified materials and manufacturers. Every item passes quality control.',
      'why.3t': 'Personal approach', 'why.3p': 'Tetyana is always available and will help you find the perfect option just for you.',
      'cats.title': 'Our categories',
      'cat.ws': "Women's socks", 'cat.ms': "Men's socks",
      'cat.wl': "Women's underwear", 'cat.ml': "Men's underwear", 'cat.br': 'Bras',
      'how.title': 'How to place an order?',
      'how.s1t': 'Choose a product', 'how.s1p': 'Browse the catalog and pick items you like',
      'how.s2t': 'Contact us', 'how.s2p': 'Message us on Telegram @NazarT84 or call Tetyana',
      'how.s3t': 'Receive your order', 'how.s3p': 'We ship via Nova Poshta & Ukrposhta across Ukraine',
      'footer.nav': 'Navigation', 'footer.cats': 'Categories',
      'footer.desc': 'Quality underwear and socks for women and men. Comfortable, stylish, affordable.',
      'footer.rights': 'All rights reserved', 'footer.copy': '© 2025 Nice Shopping',
      'footer.wl': "Women's underwear", 'footer.ml': "Men's underwear",
      'bc.home': 'Home', 'bc.catalog': 'Catalog', 'bc.contacts': 'Contacts',
      'bc.cart': 'Cart', 'bc.checkout': 'Checkout', 'bc.reviews': 'Reviews',
      'page.catalog': 'Catalog', 'page.contacts': 'Contacts',
      'page.cart': 'Cart', 'page.checkout': 'Checkout', 'page.reviews': 'Reviews',
      'filter.cat': 'Category', 'filter.all': 'All',
      'filter.ws': "Women's socks", 'filter.ms': "Men's socks",
      'filter.wl': "Women's underwear", 'filter.ml': "Men's underwear", 'filter.br': 'Bras',
      'filter.wws': "Women's winter socks", 'filter.wms': "Men's winter socks",
      'filter.sws': "Women's summer socks", 'filter.sms': "Men's summer socks",
      'filter.size': 'Size',
      'stock.in': 'In stock', 'stock.out': 'Out of stock', 'stock.pcs': 'pcs.',
      'sort.default': 'Sort by', 'sort.asc': 'Price: low to high', 'sort.desc': 'Price: high to low',
      'sort.rating': 'By rating', 'sort.discount': 'On sale',
      'info.phone': 'Phone', 'info.phone_v': '+380 95 414 18 20 — Tetyana',
      'info.delivery': 'Delivery', 'info.delivery_v': 'Nova Poshta & Ukrposhta',
      'info.hours': 'Working hours', 'info.hours_v': 'Mon–Sun: 9:00 — 21:00',
      'card.tg.t': 'Telegram', 'card.tg.p': "The fastest way to reach us. We'll reply within minutes.", 'card.tg.btn': 'Message us',
      'card.ph.t': 'Phone', 'card.ph.p': 'Tetyana is always available and happy to help you choose.', 'card.ph.btn': 'Call us',
      'form.title': 'Send a message',
      'form.nl': 'Your name *', 'form.pl': 'Phone *', 'form.ml': 'Message *',
      'form.np': 'Name', 'form.pp': '+380 XX XXX XX XX', 'form.mp': 'Your question or request...',
      'form.sub': 'Send →', 'form.ok.t': 'Message sent!', 'form.ok.p': "We'll get back to you shortly.",
      'rev.form.title': 'Leave a review',
      'rev.form.sub': 'Share your shopping experience — it helps other buyers',
      'rev.form.name': 'Your name *', 'rev.form.name.ph': 'Name',
      'rev.form.rating': 'Rating *', 'rev.form.text': 'Review *',
      'rev.form.text.ph': 'Share your shopping experience...',
      'rev.form.btn': 'Publish review →', 'rev.sending': 'Publishing...',
      'rev.ok.t': 'Thank you for your review!', 'rev.ok.p': 'Your review has been published. It means a lot to us!',
      'rev.ok.btn': 'Write another →',
      'rev.list.title': 'Customer reviews',
      'rev.empty': 'No reviews yet.<br>Be the first!',
      'cart.empty.t': 'Your cart is empty', 'cart.empty.p': 'Add items you like', 'cart.empty.btn': 'Go to catalog',
      'cart.cont': '← Continue shopping', 'cart.summ': 'Order summary',
      'cart.del': 'Delivery', 'cart.total': 'Total', 'cart.free': '✓ Free delivery',
      'cart.chk': 'Checkout', 'cart.size': 'Size', 'cart.items': 'Items',
      'cart.still': 'Only', 'cart.til': 'until free delivery',
      'co.contact': 'Contact details', 'co.first': 'First name *', 'co.last': 'Last name *',
      'co.phone': 'Phone *', 'co.email': 'Email',
      'co.del': 'Delivery (Nova Poshta / Ukrposhta)',
      'co.city': 'City *', 'co.branch': 'Branch or delivery address *',
      'co.comment': 'Order comment', 'co.payment': 'Payment',
      'co.cod': '💵 Cash on delivery', 'co.cod_d': 'Pay on receipt + postal fee',
      'co.prepay': '💳 Prepayment by card', 'co.prepay_d': "We'll send details after confirmation",
      'co.sub': 'Place order →', 'co.agree': "By clicking, you agree to the store's terms",
      'co.order': 'Your order', 'co.sending': 'Sending...',
      'co.ok.t': 'Order placed!', 'co.ok.p': "Thank you! We'll contact you shortly to confirm.", 'co.ok.btn': 'Continue shopping',
    }
  };

  function t(key) {
    return (T[LANG] && T[LANG][key] !== undefined) ? T[LANG][key] : (T.ua[key] || key);
  }

  function applyLang() {
    document.querySelectorAll('[data-i18n]').forEach(function(el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-html]').forEach(function(el) {
      el.innerHTML = t(el.getAttribute('data-i18n-html'));
    });
    document.querySelectorAll('[data-i18n-ph]').forEach(function(el) {
      el.placeholder = t(el.getAttribute('data-i18n-ph'));
    });
    var btn = document.getElementById('langBtn');
    if (btn) btn.textContent = LANG === 'ua' ? 'UA' : 'EN';
    document.documentElement.lang = LANG === 'ua' ? 'uk' : 'en';
  }

  window.LANG = LANG;
  window.i18n = t;
  window.applyLang = applyLang;
  window.toggleLang = function() {
    LANG = LANG === 'ua' ? 'en' : 'ua';
    window.LANG = LANG;
    localStorage.setItem('fp_lang', LANG);
    applyLang();
    if (typeof render === 'function') render();
    if (typeof renderCart === 'function') renderCart();
    if (typeof renderList === 'function') renderList();
  };
})();
