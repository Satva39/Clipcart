import api from "./api";

export async function applyCoupon(code) {
    const response = await api.put("/checkout/coupon", {
        code,
    });

    return response.data.data;
}