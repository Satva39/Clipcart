import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api";

const api = axios.create({
  baseURL: API_URL,
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

let refreshPromise = null;

function clearSession() {
  localStorage.removeItem("clipcart_access_token");
  localStorage.removeItem("clipcart_refresh_token");
  localStorage.removeItem("clipcart_user");
}

function setAccessToken(token) {
  localStorage.setItem("clipcart_access_token", token);
}

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("clipcart_access_token");
    config.headers = config.headers || {};

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      delete config.headers.Authorization;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

async function refreshAccessToken() {
  const refreshToken = localStorage.getItem("clipcart_refresh_token");
  if (!refreshToken) {
    throw new Error("No refresh token");
  }

  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${API_URL}/accounts/refresh`, null, {
        headers: {
          Authorization: `Bearer ${refreshToken}`,
          "Content-Type": "application/json",
        },
        withCredentials: true,
      })
      .then((response) => {
        const token = response.data.data?.access_token;
        if (!token) throw new Error("Refresh failed");
        setAccessToken(token);
        return token;
      })
      .catch((error) => {
        clearSession();
        throw error;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const status = error.response?.status;
    const url = String(originalRequest?.url || "");

    const authEndpoint =
      url.includes("/accounts/login") ||
      url.includes("/accounts/register") ||
      url.includes("/accounts/refresh");

    if (status !== 401 || authEndpoint || originalRequest?._retry) {
      if (status === 401 && authEndpoint) clearSession();
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("clipcart_refresh_token");
    if (!refreshToken) {
      clearSession();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      const token = await refreshAccessToken();
      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${token}`;
      return api(originalRequest);
    } catch {
      clearSession();
      return Promise.reject(error);
    }
  },
);

export { API_URL, clearSession };
export default api;
