import api from "./api";
import {
  getRecommendations,
  getStoreProduct,
  searchStore,
} from "./storeService";

export async function getProducts(params = {}) {
  const response = await searchStore(params);
  return response?.products || [];
}

export async function getProductById(productId) {
  return getStoreProduct(productId);
}

export async function getProductPage(params = {}) {
  return searchStore(params);
}

export async function getRelatedProducts(productId) {
  return getRecommendations({ seedProductId: productId });
}

export async function legacyProductHealth() {
  return api.get("/products/health");
}
