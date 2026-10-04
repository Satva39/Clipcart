import api from "./api";

export async function getHomeData() {
  const response = await api.get("/store/home");
  return response.data.data;
}

export async function searchStore(params = {}) {
  const response = await api.get("/store/search", { params });
  return response.data.data;
}

export async function getStoreProduct(productId) {
  const response = await api.get(`/store/product/${productId}`);
  return response.data.data;
}

export async function getStoreProductBySlug(slug) {
  const response = await api.get(`/store/products/${slug}`);
  return response.data.data;
}

export async function getStoreCategories() {
  const response = await api.get("/store/categories");
  return response.data.data || [];
}

export async function getStoreBrands() {
  const response = await api.get("/store/brands");
  return response.data.data || [];
}

export async function getRecommendations({
  viewedIds = [],
  seedProductId = null,
} = {}) {
  const response = await api.get("/store/recommendations", {
    params: {
      viewed_ids: viewedIds.join(","),
      seed_product_id: seedProductId || undefined,
      limit: 4,
    },
  });
  return response.data.data || [];
}
