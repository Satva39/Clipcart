import supplierApi from "./supplierApi";

export async function getProductVariants(productId) {
  const response = await supplierApi.get(
    `/product-variants/product/${productId}`,
  );

  return response.data.data ?? [];
}

export async function updateProductVariant(variantId, data) {
  const response = await supplierApi.put(
    `/product-variants/${variantId}`,
    data,
  );

  return response.data.data;
}

export async function deleteProductVariant(variantId) {
  const response = await supplierApi.delete(`/product-variants/${variantId}`);

  return response.data;
}

export async function getProductImages(productId) {
  const response = await supplierApi.get(
    `/product-images/product/${productId}`,
  );

  return response.data.data ?? [];
}

export async function deleteProductImage(imageId) {
  const response = await supplierApi.delete(`/product-images/${imageId}`);

  return response.data;
}

export async function setProductThumbnail(imageId) {
  const response = await supplierApi.put(
    `/product-images/${imageId}/thumbnail`,
  );

  return response.data;
}

export async function getSupplierProducts() {
  const response = await supplierApi.get("/products/supplier");

  return response.data.data ?? [];
}

export async function getSupplierProduct(productId) {
  const response = await supplierApi.get(`/products/supplier/${productId}`);

  return response.data.data;
}

export async function deleteSupplierProduct(productId) {
  const response = await supplierApi.delete(`/products/${productId}`);

  return response.data;
}

export async function updateSupplierProduct(productId, data) {
  const response = await supplierApi.put(`/products/${productId}`, data);

  return response.data;
}

export async function createSupplierProduct(data) {
  const response = await supplierApi.post("/products/", data);

  return response.data;
}

export async function getCategories() {
  const response = await supplierApi.get("/categories/");

  return response.data.data ?? [];
}

export async function getBrands() {
  const response = await supplierApi.get("/brands/");

  return response.data.data ?? [];
}

export async function createProductVariants(productId, variants) {
  const response = await supplierApi.post(
    `/product-variants/product/${productId}`,
    { variants },
  );

  return response.data.data ?? [];
}

function normalizeUploadFile(item) {
  const FileType = typeof File !== "undefined" ? File : null;
  if (FileType && item instanceof FileType) return item;
  if (FileType && item?.file instanceof FileType) return item.file;
  return null;
}

export async function uploadProductImages(
  productId,
  imageFiles,
  variantId = null,
) {
  const files = (imageFiles || []).map(normalizeUploadFile).filter(Boolean);

  if (!files.length) {
    throw new Error("No valid image files were selected.");
  }

  const formData = new FormData();
  files.forEach((file) => formData.append("images", file));

  if (variantId !== null && variantId !== undefined && variantId !== "") {
    formData.append("variant_id", String(variantId));
  }

  const response = await supplierApi.post(
    `/product-images/product/${productId}`,
    formData,
  );

  return response.data.data ?? [];
}

export async function createCategory(name) {
  const response = await supplierApi.post("/products/categories/", { name });

  return response.data;
}

export async function createBrand(name) {
  const response = await supplierApi.post("/products/brands/", { name });

  return response.data;
}

export async function deleteCategory(categoryId) {
  const response = await supplierApi.delete(
    `/products/categories/${categoryId}/`,
  );

  return response.data;
}

export async function deleteBrand(brandId) {
  const response = await supplierApi.delete(`/products/brands/${brandId}/`);

  return response.data;
}

export async function reorderProductImages(productId, imageIds) {
  const response = await supplierApi.put(
    `/product-images/product/${productId}/reorder`,
    { image_ids: imageIds },
  );

  return response.data;
}

export async function getSupplierCatalog(params = {}) {
  const response = await supplierApi.get("/supplier/portal/catalog", {
    params,
  });
  return response.data.data ?? { products: [], pagination: {} };
}
