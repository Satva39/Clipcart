import api from "./api";

export async function login(email, password) {
  const response = await api.post("/accounts/login", { email, password });
  return response.data.data;
}

export async function register(payload) {
  const response = await api.post("/accounts/register", payload);
  return response.data.data;
}

export async function getCurrentUser() {
  const response = await api.get("/accounts/me");
  return response.data.data;
}

export async function updateCurrentUser(payload) {
  const response = await api.put("/accounts/me", payload);
  return response.data.data;
}
