import axios from "axios";

const ACCESS_KEY = "clipcart_admin_access_token";
const REFRESH_KEY = "clipcart_admin_refresh_token";

export function clearAdminSession() {
  sessionStorage.removeItem(ACCESS_KEY);
  sessionStorage.removeItem(REFRESH_KEY);
  sessionStorage.removeItem("clipcart_admin_user");
}

const adminApi = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://127.0.0.1:5000/api",
  headers: { "Content-Type": "application/json" },
});

let refreshPromise = null;

adminApi.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(ACCESS_KEY);
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }

  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    if (config.headers && typeof config.headers.delete === "function") {
      config.headers.delete("Content-Type");
    } else if (config.headers) {
      delete config.headers["Content-Type"];
      delete config.headers["content-type"];
    }
  }

  return config;
});

adminApi.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config || {};
    const isAuthRoute = String(original.url || "").includes("/admin/auth/");
    if (error.response?.status !== 401 || original._adminRetry || isAuthRoute) {
      return Promise.reject(error);
    }

    const refreshToken = sessionStorage.getItem(REFRESH_KEY);
    if (!refreshToken) {
      clearAdminSession();
      window.location.href = "/login";
      return Promise.reject(error);
    }

    try {
      if (!refreshPromise) {
        refreshPromise = axios.post(
          `${adminApi.defaults.baseURL}/admin/auth/refresh`,
          {},
          { headers: { Authorization: `Bearer ${refreshToken}` } },
        );
      }
      const refreshed = await refreshPromise;
      const accessToken = refreshed.data?.data?.access_token;
      if (!accessToken) throw new Error("Invalid admin refresh response.");

      sessionStorage.setItem(ACCESS_KEY, accessToken);
      original._adminRetry = true;
      original.headers = original.headers || {};
      original.headers.Authorization = `Bearer ${accessToken}`;
      return adminApi(original);
    } catch (refreshError) {
      clearAdminSession();
      window.location.href = "/login";
      return Promise.reject(refreshError);
    } finally {
      refreshPromise = null;
    }
  },
);

export default adminApi;
