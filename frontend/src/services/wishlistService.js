import api from "./api";

export async function getWishlist() {
    const response = await api.get("/wishlist/");
    return response.data.data ?? [];
}

export async function addToWishlist(productId) {
    const response = await api.post(
        `/wishlist/${productId}`
    );

    return response.data;
}

export async function removeFromWishlist(productId) {
    const response = await api.delete(
        `/wishlist/${productId}`
    );

    return response.data;
}