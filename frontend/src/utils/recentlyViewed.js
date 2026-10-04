const KEY = "clipcart_recently_viewed";
const LIMIT = 12;

function read() {
  try {
    const raw = localStorage.getItem(KEY);
    const value = raw ? JSON.parse(raw) : [];
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function getRecentlyViewed() {
  return read();
}

export function rememberRecentlyViewed(product) {
  if (!product?.id) return;

  const entry = {
    id: product.id,
    name: product.name,
    slug: product.slug,
    price: product.price,
    compare_price: product.compare_price,
    discount_percent: product.discount_percent,
    stock: product.stock,
    image: product.image,
    category: product.category,
    brand: product.brand,
    rating: product.rating,
    review_count: product.review_count,
  };

  const next = [
    entry,
    ...read().filter((item) => Number(item.id) !== Number(product.id)),
  ].slice(0, LIMIT);
  localStorage.setItem(KEY, JSON.stringify(next));
}

export function getRecentlyViewedIds() {
  return read()
    .map((item) => item.id)
    .filter(Boolean);
}
