export function formatCurrency(value) {
  return `₹${Number(value || 0).toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  })}`;
}

export function discountPercent(price, comparePrice) {
  const current = Number(price || 0);
  const compare = Number(comparePrice || 0);
  if (!compare || compare <= current) return 0;
  return Math.round(((compare - current) / compare) * 100);
}

export function getProductImage(product, variantId = null) {
  const variant = product?.variants?.find(
    (item) => Number(item.id) === Number(variantId),
  );
  const variantImage = variant?.images?.[0]?.url;
  if (variantImage) return variantImage;

  const images = product?.images || [];
  const primary = images.find((image) => image.primary);
  return primary?.url || images[0]?.url || product?.image || null;
}

export function getCategoryName(category) {
  return typeof category === "object" ? category?.name : category;
}

export function getBrandName(brand) {
  return typeof brand === "object" ? brand?.name : brand;
}

export function slugify(value) {
  return String(value || "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, "");
}

export function formatDate(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}
