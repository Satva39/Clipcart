export function getApiMessage(
  error,
  fallback = "Something went wrong. Please try again.",
) {
  const response = error?.response?.data;
  if (typeof response?.message === "string") return response.message;
  if (response?.errors && typeof response.errors === "object") {
    const first = Object.values(response.errors).flat?.()[0];
    if (first) return String(first);
  }
  if (typeof error?.message === "string" && error.message !== "Network Error") {
    return error.message;
  }
  return fallback;
}
