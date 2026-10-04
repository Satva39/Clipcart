import adminApi from "./api";

export async function getAdminProfile() {
  const response = await adminApi.get("/admin/profile");
  return response.data.data;
}

export async function changeAdminPassword(
  currentPassword,
  newPassword,
  confirmPassword,
) {
  const response = await adminApi.put("/admin/profile/password", {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return response.data;
}
