import axios from "axios";

export const ACCESS_KEY = "clipcart_logistics_access_token";
export const REFRESH_KEY = "clipcart_logistics_refresh_token";
export const USER_KEY = "clipcart_logistics_user";

const baseURL = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

const api = axios.create({
  baseURL,
  headers: { "Content-Type": "application/json" },
});

let refreshPromise = null;

function clearSession() {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

function shouldSkipRefresh(config) {
  return (
    config?.url?.includes("/logistics/auth/login") ||
    config?.url?.includes("/accounts/refresh")
  );
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(ACCESS_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;

    if (
      error.response?.status !== 401 ||
      !original ||
      original._retry ||
      shouldSkipRefresh(original)
    ) {
      if (error.response?.status === 401 && !shouldSkipRefresh(original)) {
        clearSession();
        window.location.href = "/login";
      }
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) {
      clearSession();
      window.location.href = "/login";
      return Promise.reject(error);
    }

    original._retry = true;

    try {
      refreshPromise ||= axios
        .post(
          `${baseURL}/accounts/refresh`,
          {},
          {
            headers: {
              Authorization: `Bearer ${refreshToken}`,
              "Content-Type": "application/json",
            },
          },
        )
        .then((response) => {
          const accessToken = response.data?.data?.access_token;
          if (!accessToken) {
            throw new Error("Session refresh failed.");
          }
          localStorage.setItem(ACCESS_KEY, accessToken);
          return accessToken;
        })
        .finally(() => {
          refreshPromise = null;
        });

      const accessToken = await refreshPromise;
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${accessToken}`;
      return api(original);
    } catch (refreshError) {
      clearSession();
      window.location.href = "/login";
      return Promise.reject(refreshError);
    }
  },
);

export { clearSession };
export default api;
