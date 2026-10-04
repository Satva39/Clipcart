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

export async function getMyReviews(productId) {
  const suffix = productId ? `?product_id=${Number(productId)}` : "";
  const response = await api.get(`/reviews/mine${suffix}`);
  return response.data.data ?? [];
}

export async function createReview(data) {
  const response = await api.post("/reviews/", data);
  return response.data;
}

export async function updateReview(reviewId, data) {
  const response = await api.put(`/reviews/${reviewId}`, data);
  return response.data.data?.review ?? response.data.data;
}

export async function deleteReview(reviewId) {
  const response = await api.delete(`/reviews/${reviewId}`);
  return response.data;
}
