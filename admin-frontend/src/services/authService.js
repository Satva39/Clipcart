import adminApi, { clearAdminSession } from "./api";

export async function loginAdmin(email, password) {
  localStorage.removeItem("clipcart_admin_access_token");
  localStorage.removeItem("clipcart_admin_refresh_token");
  localStorage.removeItem("clipcart_admin_user");
  const response = await adminApi.post("/admin/auth/login", {
    email,
    password,
  });
  const data = response.data.data;
  sessionStorage.setItem("clipcart_admin_access_token", data.access_token);
  sessionStorage.setItem("clipcart_admin_refresh_token", data.refresh_token);
  sessionStorage.setItem("clipcart_admin_user", JSON.stringify(data.user));
  return data;
}

export async function forgotAdminPassword(email) {
  const response = await adminApi.post("/admin/auth/forgot-password", {
    email,
  });
  return response.data;
}

export async function resetAdminPassword(token, password, confirmPassword) {
  const response = await adminApi.post("/admin/auth/reset-password", {
    token,
    password,
    confirm_password: confirmPassword,
  });
  return response.data;
}

export async function logoutAdmin() {
  try {
    await adminApi.post("/admin/auth/logout", {
      refresh_token:
        sessionStorage.getItem("clipcart_admin_refresh_token") || "",
    });
  } finally {
    clearAdminSession();
  }
}
