import supplierApi from "./supplierApi";

export async function getPayoutAccount() {
    const response = await supplierApi.get(
        "/payouts/account"
    );

    return response.data.data;
}

export async function savePayoutAccount(data) {
    const response = await supplierApi.post(
        "/payouts/account",
        data
    );

    return response.data;
}

export async function getPayoutBalance() {
    const response = await supplierApi.get(
        "/payouts/balance"
    );

    return response.data.data;
}

export async function requestPayout(amount) {
    const response = await supplierApi.post(
        "/payouts/request",
        {
            amount,
        }
    );

    return response.data;
}

export async function getPayoutHistory() {
    const response = await supplierApi.get(
        "/payouts/history"
    );

    return response.data.data ?? [];
}