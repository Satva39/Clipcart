import api from "./api";

function normalizeProductId(productId) {
    const value = String(productId);

    if (value.includes("-")) {
        return Number(value.split("-")[0]);
    }

    return Number(value);
}

function normalizeVariantId(variantId) {
    if (
        variantId === null ||
        variantId === undefined ||
        variantId === "" ||
        variantId === "default"
    ) {
        return null;
    }

    return Number(variantId);
}

export async function getCart() {
    const response = await api.get("/cart/");
    return response.data.data;
}

export async function addToCart(
    productId,
    quantity = 1,
    variantId = null
) {
    const response = await api.post("/cart/", {
        product_id: normalizeProductId(productId),
        variant_id: normalizeVariantId(variantId),
        quantity: Number(quantity),
    });

    return response.data;
}

export async function updateCart(
    productId,
    quantity,
    variantId = null
) {
    const response = await api.put("/cart/", {
        product_id: normalizeProductId(productId),
        variant_id: normalizeVariantId(variantId),
        quantity: Number(quantity),
    });

    return response.data;
}

export async function removeFromCart(
    productId,
    variantId = null
) {
    const response = await api.delete("/cart/", {
        data: {
            product_id: normalizeProductId(productId),
            variant_id: normalizeVariantId(variantId),
        },
    });

    return response.data;
}