import api from "./api";

export async function getProductReviews(productId) {
  const response = await api.get(`/reviews/product/${productId}`);
  return (
    response.data.data ?? {
      reviews: [],
      summary: { average: 0, count: 0, distribution: {} },
    }
  );
}

export async function getMyReviews(productId, orderId = null) {
  const params = new URLSearchParams();
  if (productId) params.set("product_id", String(Number(productId)));
  if (orderId) params.set("order_id", String(Number(orderId)));
  const suffix = params.toString() ? `?${params.toString()}` : "";
  const response = await api.get(`/reviews/mine${suffix}`);
  return response.data.data ?? [];
}

export async function createReview(data, mediaFiles = []) {
  const formData = new FormData();
  formData.append("product_id", String(data.product_id));
  formData.append("order_item_id", String(data.order_item_id));
  formData.append("rating", String(data.rating));
  formData.append("title", data.title || "");
  formData.append("review", data.review || "");
  (mediaFiles || []).forEach((file) => formData.append("media", file));

  const response = await api.post("/reviews/", formData);
  return response.data.data;
}

export async function updateReview(reviewId, data) {
  const response = await api.put(`/reviews/${reviewId}`, data);
  return response.data.data?.review ?? response.data.data;
}

export async function deleteReview(reviewId) {
  const response = await api.delete(`/reviews/${reviewId}`);
  return response.data;
}
