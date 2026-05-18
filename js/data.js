var PRODUCTS = [];

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
