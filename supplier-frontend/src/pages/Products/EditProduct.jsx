import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  FaArrowLeft,
  FaCheck,
  FaImage,
  FaPlus,
  FaSave,
  FaStar,
  FaTimes,
  FaTrash,
} from "react-icons/fa";
import {
  deleteProductImage,
  deleteProductVariant,
  getBrands,
  getCategories,
  createProductVariants,
  getProductImages,
  getProductVariants,
  getSupplierProduct,
  reorderProductImages,
  setProductThumbnail,
  updateProductVariant,
  updateSupplierProduct,
  uploadProductImages,
} from "../../services/productService";
import "../../styles/supplier-pages.css";
import "./add-product.css";

const imageTypes = ["image/jpeg", "image/png", "image/webp"];

const normalizeVariant = (variant) => ({
  ...variant,
  localId: `server-${variant.id}`,
  dirty: false,
  options: Object.entries(variant.option_values || {}).map(([name, value]) => ({
    name,
    value,
  })),
  images: variant.images || [],
});

const asLines = (value) => (Array.isArray(value) ? value.join("\n") : "");
const asSpecs = (value) =>
  value && typeof value === "object"
    ? Object.entries(value)
        .map(([key, val]) => `${key}: ${val}`)
        .join("\n")
    : "";

function makeLocalId(prefix = "item") {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

const createBlankVariant = (defaultPrice = "") => ({
  localId: makeLocalId("variant"),
  id: null,
  dirty: true,
  options: [{ name: "", value: "" }],
  sku: "",
  price: defaultPrice,
  compare_price: "",
  stock: "0",
  is_active: true,
  images: [],
});

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
  disabled = false,
  min,
  step,
  placeholder,
}) {
  return (
    <label className="form-label">
      <span>{label}</span>
      <input
        className="form-control"
        value={value ?? ""}
        onChange={(event) => onChange(event.target.value)}
        type={type}
        required={required}
        disabled={disabled}
        min={min}
        step={step}
        placeholder={placeholder}
      />
    </label>
  );
}

export default function EditProduct() {
  const { productId } = useParams();
  const navigate = useNavigate();
  const productImageInputRef = useRef(null);
  const variantImageInputRefs = useRef(new Map());

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [variantBusy, setVariantBusy] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [images, setImages] = useState([]);
  const [variants, setVariants] = useState([]);
  const [form, setForm] = useState({
    name: "",
    sku: "",
    description: "",
    highlights: "",
    specifications: "",
    category_id: "",
    brand_id: "",
    price: "",
    compare_price: "",
    stock: "0",
    low_stock_threshold: "5",
    shipping_weight_kg: "",
    shipping_length_cm: "",
    shipping_width_cm: "",
    shipping_height_cm: "",
    status: "ACTIVE",
    is_featured: false,
  });

  const hasVariants = variants.length > 0;
  const variantStock = useMemo(
    () =>
      variants.reduce(
        (sum, variant) => sum + Math.max(0, Number(variant.stock) || 0),
        0,
      ),
    [variants],
  );

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const [product, categoryData, brandData, imageData, variantData] =
        await Promise.all([
          getSupplierProduct(productId),
          getCategories(),
          getBrands(),
          getProductImages(productId),
          getProductVariants(productId),
        ]);

      setCategories(categoryData || []);
      setBrands(brandData || []);
      setImages(
        [...(imageData || [])].sort(
          (a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0),
        ),
      );
      setVariants((variantData || []).map(normalizeVariant));
      setForm({
        name: product.name || "",
        sku: product.sku || "",
        description: product.description || "",
        highlights: asLines(product.highlights),
        specifications: asSpecs(product.specifications),
        category_id: product.category_id ?? "",
        brand_id: product.brand_id ?? "",
        price: product.price ?? "",
        compare_price: product.compare_price ?? "",
        stock: product.stock ?? "0",
        low_stock_threshold: product.low_stock_threshold ?? "5",
        shipping_weight_kg: product.shipping_weight_kg ?? "",
        shipping_length_cm: product.shipping_length_cm ?? "",
        shipping_width_cm: product.shipping_width_cm ?? "",
        shipping_height_cm: product.shipping_height_cm ?? "",
        status: product.status || "ACTIVE",
        is_featured: Boolean(product.is_featured),
      });
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to load product.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [productId]);

  const update = (key, value) =>
    setForm((current) => ({ ...current, [key]: value }));

  const parseJsonFields = () => ({
    highlights: form.highlights
      .split("\n")
      .map((item) => item.trim())
      .filter(Boolean),
    specifications: Object.fromEntries(
      form.specifications
        .split("\n")
        .map((line) => line.split(":"))
        .map(([key, ...rest]) => [
          String(key || "").trim(),
          rest.join(":").trim(),
        ])
        .filter(([key, value]) => key && value),
    ),
  });

  const validateImages = (files) => {
    const selected = Array.from(files || []);
    const invalid = selected.filter((file) => !imageTypes.includes(file.type));
    if (invalid.length) {
      throw new Error("Only JPG, PNG and WebP image files are supported.");
    }
    const oversized = selected.find((file) => file.size > 10 * 1024 * 1024);
    if (oversized) {
      throw new Error("Each image must be 10 MB or smaller.");
    }
    return selected;
  };

  async function persistVariant(variant) {
    const options = variant.options
      .map((option) => ({
        name: String(option.name || "").trim(),
        value: String(option.value || "").trim(),
      }))
      .filter((option) => option.name && option.value);

    if (!options.length || options.length !== variant.options.length) {
      throw new Error("Every variant option needs both a name and a value.");
    }

    const sku =
      String(variant.sku || "").trim() ||
      `${String(form.sku || "CLP").trim()}-${makeLocalId("VAR").slice(-12)}`;
    const price = Number(
      variant.price === "" ? form.price || 0 : variant.price,
    );
    const comparePrice =
      variant.compare_price === "" || variant.compare_price == null
        ? null
        : Number(variant.compare_price);
    const stock = Number(variant.stock || 0);

    if (!Number.isFinite(price) || price < 0) {
      throw new Error(`Invalid price for ${sku}.`);
    }
    if (
      comparePrice !== null &&
      (!Number.isFinite(comparePrice) || comparePrice < price)
    ) {
      throw new Error(
        `Compare / MRP must be greater than or equal to ${sku}'s price.`,
      );
    }
    if (!Number.isInteger(stock) || stock < 0) {
      throw new Error(`Stock for ${sku} must be a whole number.`);
    }

    const payload = {
      options,
      sku,
      price,
      compare_price: comparePrice,
      stock,
      is_active: Boolean(variant.is_active),
    };

    let persistedId = variant.id;
    if (persistedId) {
      await updateProductVariant(persistedId, payload);
    } else {
      const created = await createProductVariants(productId, [payload]);
      const createdVariant = Array.isArray(created) ? created[0] : null;
      if (!createdVariant?.id) {
        throw new Error("The server did not return the new variant ID.");
      }
      persistedId = createdVariant.id;
    }

    const pendingImages = (variant.images || [])
      .filter((image) => image?.file instanceof File)
      .map((image) => ({ file: image.file }));

    if (pendingImages.length) {
      await uploadProductImages(productId, pendingImages, persistedId);
    }

    return persistedId;
  }

  async function saveProduct(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      if (!form.name.trim()) throw new Error("Product name is required.");
      if (!form.category_id) throw new Error("Select a category.");
      if (!form.sku.trim()) throw new Error("SKU is required.");

      const productPayload = {
        name: form.name.trim(),
        sku: form.sku.trim(),
        description: form.description.trim(),
        ...parseJsonFields(),
        category_id: Number(form.category_id),
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        price: Number(form.price),
        compare_price:
          form.compare_price === "" ? null : Number(form.compare_price),
        stock: hasVariants ? variantStock : Number(form.stock || 0),
        low_stock_threshold: Number(form.low_stock_threshold || 5),
        shipping_weight_kg:
          form.shipping_weight_kg === ""
            ? null
            : Number(form.shipping_weight_kg),
        shipping_length_cm:
          form.shipping_length_cm === ""
            ? null
            : Number(form.shipping_length_cm),
        shipping_width_cm:
          form.shipping_width_cm === "" ? null : Number(form.shipping_width_cm),
        shipping_height_cm:
          form.shipping_height_cm === ""
            ? null
            : Number(form.shipping_height_cm),
        status: form.status,
        is_featured: Boolean(form.is_featured),
      };

      if (!Number.isFinite(productPayload.price) || productPayload.price < 0) {
        throw new Error("Selling price must be a valid non-negative number.");
      }
      if (
        productPayload.compare_price !== null &&
        (!Number.isFinite(productPayload.compare_price) ||
          productPayload.compare_price < productPayload.price)
      ) {
        throw new Error(
          "Compare / MRP must be greater than or equal to the selling price.",
        );
      }

      const updated = await updateSupplierProduct(productId, productPayload);

      const dirtyVariants = variants.filter(
        (variant) => variant.dirty || !variant.id,
      );
      if (dirtyVariants.length) {
        for (const variant of dirtyVariants) {
          await persistVariant(variant);
        }
      }

      const [freshProduct, freshVariants] = await Promise.all([
        getSupplierProduct(productId),
        getProductVariants(productId),
      ]);

      // Rehydrate the form from the just-persisted server representation. This prevents
      // a successful edit from visually snapping back to the previous value.
      const savedProduct = freshProduct || updated?.data || updated;
      if (savedProduct) {
        setForm((current) => ({
          ...current,
          name: savedProduct.name ?? current.name,
          sku: savedProduct.sku ?? current.sku,
          description: savedProduct.description ?? current.description,
          price: savedProduct.price ?? current.price,
          compare_price:
            savedProduct.compare_price === null
              ? ""
              : (savedProduct.compare_price ?? current.compare_price),
          stock: savedProduct.stock ?? current.stock,
          low_stock_threshold:
            savedProduct.low_stock_threshold ?? current.low_stock_threshold,
          shipping_weight_kg:
            savedProduct.shipping_weight_kg ?? current.shipping_weight_kg,
          shipping_length_cm:
            savedProduct.shipping_length_cm ?? current.shipping_length_cm,
          shipping_width_cm:
            savedProduct.shipping_width_cm ?? current.shipping_width_cm,
          shipping_height_cm:
            savedProduct.shipping_height_cm ?? current.shipping_height_cm,
          category_id: savedProduct.category_id ?? current.category_id,
          brand_id: savedProduct.brand_id ?? current.brand_id,
          status: savedProduct.status ?? current.status,
          is_featured: Boolean(savedProduct.is_featured ?? current.is_featured),
        }));
      }

      setVariants((freshVariants || []).map(normalizeVariant));
      setMessage(
        dirtyVariants.length
          ? "Product and variant changes saved successfully."
          : "Product changes saved successfully.",
      );
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to save product changes.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function uploadImages(files, variantId = null) {
    const selected = validateImages(files);
    if (!selected.length) return;

    setUploading(true);
    setError("");
    try {
      const uploaded = await uploadProductImages(
        productId,
        selected.map((file) => ({ file })),
        variantId,
      );

      if (variantId) {
        const next = await getProductVariants(productId);
        setVariants((next || []).map(normalizeVariant));
      } else {
        const next = await getProductImages(productId);
        setImages(
          [...(next || [])].sort(
            (a, b) => Number(a.sort_order || 0) - Number(b.sort_order || 0),
          ),
        );
      }

      setMessage(
        `${uploaded.length || selected.length} image${(uploaded.length || selected.length) === 1 ? "" : "s"} uploaded successfully.`,
      );
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to upload images.",
      );
    } finally {
      setUploading(false);
    }
  }

  async function handleProductImageSelect(event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;
    await uploadImages(files);
  }

  async function handleVariantUpload(variant, event) {
    const files = Array.from(event.target.files || []);
    event.target.value = "";
    if (!files.length) return;

    try {
      validateImages(files);
    } catch (err) {
      setError(err.message);
      return;
    }

    if (!variant.id) {
      const pending = files.map((file) => ({
        localId: makeLocalId("image"),
        file,
        image_url: URL.createObjectURL(file),
        name: file.name,
      }));

      setVariants((current) =>
        current.map((item) =>
          item.localId === variant.localId
            ? {
                ...item,
                dirty: true,
                images: [...(item.images || []), ...pending],
              }
            : item,
        ),
      );
      setMessage(
        `${files.length} variant image${files.length === 1 ? "" : "s"} queued. Save the variant.`,
      );
      return;
    }

    await uploadImages(files, variant.id);
  }

  async function removeImage(imageId) {
    if (!window.confirm("Delete this product image?")) return;
    try {
      await deleteProductImage(imageId);
      setImages((current) => current.filter((image) => image.id !== imageId));
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to delete image.");
    }
  }

  async function makeThumbnail(imageId) {
    try {
      await setProductThumbnail(imageId);
      setImages((current) =>
        current.map((image) => ({
          ...image,
          is_thumbnail: image.id === imageId,
        })),
      );
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to update thumbnail.");
    }
  }

  async function moveImage(index, direction) {
    const nextIndex = index + direction;
    if (nextIndex < 0 || nextIndex >= images.length) return;
    const next = [...images];
    [next[index], next[nextIndex]] = [next[nextIndex], next[index]];
    setImages(next);
    try {
      await reorderProductImages(
        productId,
        next.map((image) => image.id),
      );
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to reorder images.");
      load();
    }
  }

  function updateVariant(localId, key, value) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId
          ? { ...variant, [key]: value, dirty: true }
          : variant,
      ),
    );
  }

  function updateVariantOption(localId, optionIndex, key, value) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId
          ? {
              ...variant,
              dirty: true,
              options: variant.options.map((option, index) =>
                index === optionIndex ? { ...option, [key]: value } : option,
              ),
            }
          : variant,
      ),
    );
  }

  function addVariantOption(localId) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId
          ? {
              ...variant,
              dirty: true,
              options: [...variant.options, { name: "", value: "" }],
            }
          : variant,
      ),
    );
  }

  function removeVariantOption(localId, optionIndex) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId
          ? {
              ...variant,
              dirty: true,
              options: variant.options.filter(
                (_, index) => index !== optionIndex,
              ),
            }
          : variant,
      ),
    );
  }

  async function saveVariant(variant) {
    setVariantBusy(variant.localId);
    setError("");
    try {
      await persistVariant(variant);
      const next = await getProductVariants(productId);
      setVariants((next || []).map(normalizeVariant));
      setMessage("Variant saved successfully.");
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to save variant.",
      );
    } finally {
      setVariantBusy(null);
    }
  }

  async function removeVariant(variant) {
    if (!variant.id) {
      setVariants((current) =>
        current.filter((item) => item.localId !== variant.localId),
      );
      return;
    }
    if (!window.confirm(`Delete variant ${variant.sku || variant.id}?`)) return;

    setVariantBusy(variant.localId);
    try {
      await deleteProductVariant(variant.id);
      setVariants((current) =>
        current.filter((item) => item.id !== variant.id),
      );
      setMessage("Variant deleted successfully.");
    } catch (err) {
      setError(err?.response?.data?.message || "Unable to delete variant.");
    } finally {
      setVariantBusy(null);
    }
  }

  function addVariant() {
    setVariants((current) => [...current, createBlankVariant(form.price)]);
  }

  if (loading) {
    return <div className="table-skeleton">Loading product workspace…</div>;
  }

  return (
    <div className="page-shell supplier-product-editor">
      <div className="page-heading product-editor-heading">
        <div>
          <button
            className="ghost-link"
            type="button"
            onClick={() => navigate("/products")}
          >
            <FaArrowLeft /> Back to products
          </button>
          <div className="editor-heading-row">
            <div>
              <span className="editor-kicker">Product workspace</span>
              <h2>Edit product</h2>
              <p>
                Update listing, pricing, inventory, images and variants in one
                place.
              </p>
            </div>
            <div className="editor-save-indicator">
              {saving
                ? "Saving changes…"
                : "All changes stay here until you save."}
            </div>
          </div>
        </div>
      </div>

      {error ? <div className="notice error">{error}</div> : null}
      {message ? <div className="notice success">{message}</div> : null}

      <form onSubmit={saveProduct} className="product-editor">
        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Basic information</h3>
              <p className="panel-subtitle">
                Customer-facing information and catalog identity.
              </p>
            </div>
            <span
              className={`status-pill ${String(form.status).toLowerCase()}`}
            >
              {form.status}
            </span>
          </div>
          <div className="form-grid-2">
            <Field
              label="Product name"
              value={form.name}
              onChange={(value) => update("name", value)}
              required
              placeholder="e.g. Classic Desk Calendar"
            />
            <Field
              label="Product SKU"
              value={form.sku}
              onChange={(value) => update("sku", value)}
              required
              placeholder="e.g. CLP-CAL-001"
            />
          </div>
          <label className="form-label">
            <span>Description</span>
            <textarea
              className="form-control form-textarea editor-textarea-lg"
              value={form.description}
              onChange={(event) => update("description", event.target.value)}
              required
              placeholder="Describe the product clearly for customers."
            />
          </label>
          <div className="form-grid-2">
            <label className="form-label">
              <span>
                Highlights <em>one per line</em>
              </span>
              <textarea
                className="form-control form-textarea"
                value={form.highlights}
                onChange={(event) => update("highlights", event.target.value)}
                placeholder="Premium paper\nCompact desk size"
              />
            </label>
            <label className="form-label">
              <span>
                Specifications <em>Key: value per line</em>
              </span>
              <textarea
                className="form-control form-textarea"
                value={form.specifications}
                onChange={(event) =>
                  update("specifications", event.target.value)
                }
                placeholder="Material: Paper\nSize: A4"
              />
            </label>
          </div>
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Catalog & pricing</h3>
              <p className="panel-subtitle">
                Change these values and save once. They will not reset while you
                edit.
              </p>
            </div>
          </div>
          <div className="form-grid-2">
            <label className="form-label">
              <span>Category</span>
              <select
                className="form-control"
                value={form.category_id}
                onChange={(event) => update("category_id", event.target.value)}
                required
              >
                <option value="">Select category</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="form-label">
              <span>Brand</span>
              <select
                className="form-control"
                value={form.brand_id}
                onChange={(event) => update("brand_id", event.target.value)}
              >
                <option value="">No brand</option>
                {brands.map((brand) => (
                  <option key={brand.id} value={brand.id}>
                    {brand.name}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="form-grid-3">
            <Field
              label="Selling price"
              type="number"
              step="0.01"
              min="0"
              value={form.price}
              onChange={(value) => update("price", value)}
              required
            />
            <Field
              label="Compare / MRP"
              type="number"
              step="0.01"
              min="0"
              value={form.compare_price}
              onChange={(value) => update("compare_price", value)}
            />
            <Field
              label="Low-stock threshold"
              type="number"
              min="0"
              value={form.low_stock_threshold}
              onChange={(value) => update("low_stock_threshold", value)}
            />
          </div>
          <div className="form-grid-2 editor-toggle-row">
            <label className="form-label">
              <span>Status</span>
              <select
                className="form-control"
                value={form.status}
                onChange={(event) => update("status", event.target.value)}
              >
                <option value="ACTIVE">Active</option>
                <option value="INACTIVE">Inactive</option>
              </select>
            </label>
            <label className="check-control editor-check">
              <input
                type="checkbox"
                checked={form.is_featured}
                onChange={(event) =>
                  update("is_featured", event.target.checked)
                }
              />
              <FaStar /> Featured product
            </label>
          </div>
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Product images</h3>
              <p className="panel-subtitle">
                Select multiple images from your computer. Upload happens
                immediately.
              </p>
            </div>
            <button
              type="button"
              className="editor-btn primary"
              onClick={() => productImageInputRef.current?.click()}
              disabled={uploading}
            >
              <FaImage /> {uploading ? "Uploading…" : "Add images"}
            </button>
            <input
              ref={productImageInputRef}
              className="supplier-file-input supplier-file-input-native"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              disabled={uploading}
              onChange={handleProductImageSelect}
            />
          </div>
          {images.length ? (
            <div className="editor-image-gallery">
              {images.map((image, index) => (
                <div
                  key={image.id}
                  className={`editor-image-tile ${image.is_thumbnail ? "primary" : ""}`}
                >
                  <div className="editor-image-preview">
                    <img
                      src={image.image_url}
                      alt={form.name || "Product"}
                      loading="lazy"
                      decoding="async"
                    />
                    {image.is_thumbnail ? <span>Primary</span> : null}
                  </div>
                  <div className="editor-image-actions">
                    <button
                      type="button"
                      title="Set as primary"
                      className={image.is_thumbnail ? "active" : ""}
                      onClick={() => makeThumbnail(image.id)}
                    >
                      <FaCheck />
                    </button>
                    <button
                      type="button"
                      title="Move left"
                      disabled={index === 0}
                      onClick={() => moveImage(index, -1)}
                    >
                      <FaArrowLeft />
                    </button>
                    <button
                      type="button"
                      title="Move right"
                      disabled={index === images.length - 1}
                      onClick={() => moveImage(index, 1)}
                    >
                      <FaArrowLeft style={{ transform: "rotate(180deg)" }} />
                    </button>
                    <button
                      type="button"
                      title="Delete image"
                      className="danger"
                      onClick={() => removeImage(image.id)}
                    >
                      <FaTrash />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="editor-empty-media">
              <FaImage />
              <div>
                <strong>No product images yet</strong>
                <span>Add one or more clear product photos.</span>
              </div>
              <button
                type="button"
                className="editor-btn secondary"
                onClick={() => productImageInputRef.current?.click()}
              >
                Choose from PC
              </button>
            </div>
          )}
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Shipping package</h3>
              <p className="panel-subtitle">
                Use the real packed dimensions and weight for courier
                fulfillment.
              </p>
            </div>
          </div>
          <div className="form-grid-4">
            <Field
              label="Weight (kg)"
              type="number"
              value={form.shipping_weight_kg}
              onChange={(value) => update("shipping_weight_kg", value)}
              placeholder="e.g. 0.50"
            />
            <Field
              label="Length (cm)"
              type="number"
              value={form.shipping_length_cm}
              onChange={(value) => update("shipping_length_cm", value)}
              placeholder="e.g. 20"
            />
            <Field
              label="Width (cm)"
              type="number"
              value={form.shipping_width_cm}
              onChange={(value) => update("shipping_width_cm", value)}
              placeholder="e.g. 15"
            />
            <Field
              label="Height (cm)"
              type="number"
              value={form.shipping_height_cm}
              onChange={(value) => update("shipping_height_cm", value)}
              placeholder="e.g. 8"
            />
          </div>
          <p className="panel-subtitle">
            All four values are required before a real courier shipment can be
            created. Variants use this product package profile.
          </p>
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Inventory</h3>
              <p className="panel-subtitle">
                Stock is calculated from variants when variants exist.
              </p>
            </div>
            <div className="editor-stock-summary">
              <span>Sellable stock</span>
              <strong>
                {hasVariants ? variantStock : Number(form.stock || 0)}
              </strong>
            </div>
          </div>
          <Field
            label="Base product stock"
            type="number"
            min="0"
            value={hasVariants ? String(variantStock) : form.stock}
            disabled={hasVariants}
            onChange={(value) => update("stock", value)}
          />
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">Variants</h3>
              <p className="panel-subtitle">
                Add sellable combinations such as Color + Storage. Save a
                variant directly or save the whole product.
              </p>
            </div>
            <button
              type="button"
              className="editor-btn primary"
              onClick={addVariant}
            >
              <FaPlus /> Add variant
            </button>
          </div>

          {variants.length ? (
            <div className="editor-variant-list">
              {variants.map((variant, variantIndex) => (
                <div
                  key={variant.localId || variant.id}
                  className={`editor-variant-card ${variant.dirty ? "dirty" : ""}`}
                >
                  <div className="editor-variant-head">
                    <div>
                      <span>Variant {variantIndex + 1}</span>
                      <strong>
                        {variant.options
                          .map((option) => `${option.name}: ${option.value}`)
                          .filter(Boolean)
                          .join(" · ") || "New variant"}
                      </strong>
                    </div>
                    <div className="editor-inline-actions">
                      <button
                        type="button"
                        className="editor-btn secondary small"
                        onClick={() =>
                          variantImageInputRefs.current
                            .get(variant.localId)
                            ?.click()
                        }
                        disabled={variantBusy === variant.localId}
                      >
                        <FaImage /> Images
                      </button>
                      <input
                        ref={(element) => {
                          if (element)
                            variantImageInputRefs.current.set(
                              variant.localId,
                              element,
                            );
                          else
                            variantImageInputRefs.current.delete(
                              variant.localId,
                            );
                        }}
                        className="supplier-file-input supplier-file-input-native"
                        type="file"
                        accept="image/jpeg,image/png,image/webp"
                        multiple
                        onChange={(event) =>
                          handleVariantUpload(variant, event)
                        }
                      />
                      <button
                        type="button"
                        className="editor-icon-btn danger"
                        onClick={() => removeVariant(variant)}
                        disabled={variantBusy === variant.localId}
                        title="Delete variant"
                      >
                        <FaTrash />
                      </button>
                    </div>
                  </div>

                  <div className="editor-variant-options">
                    {variant.options.map((option, optionIndex) => (
                      <div
                        className="editor-option-row"
                        key={`${variant.localId}-${optionIndex}`}
                      >
                        <input
                          className="form-control"
                          placeholder="Option name e.g. Color"
                          value={option.name}
                          onChange={(event) =>
                            updateVariantOption(
                              variant.localId,
                              optionIndex,
                              "name",
                              event.target.value,
                            )
                          }
                        />
                        <input
                          className="form-control"
                          placeholder="Value e.g. Green"
                          value={option.value}
                          onChange={(event) =>
                            updateVariantOption(
                              variant.localId,
                              optionIndex,
                              "value",
                              event.target.value,
                            )
                          }
                        />
                        <button
                          type="button"
                          className="editor-icon-btn subtle"
                          disabled={variant.options.length <= 1}
                          onClick={() =>
                            removeVariantOption(variant.localId, optionIndex)
                          }
                          title="Remove option"
                        >
                          <FaTimes />
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="editor-text-btn"
                      onClick={() => addVariantOption(variant.localId)}
                    >
                      <FaPlus /> Add option
                    </button>
                  </div>

                  <div className="form-grid-4 editor-variant-fields">
                    <Field
                      label="SKU"
                      value={variant.sku}
                      onChange={(value) =>
                        updateVariant(variant.localId, "sku", value)
                      }
                      placeholder="Auto-generated if blank"
                    />
                    <Field
                      label="Price"
                      type="number"
                      step="0.01"
                      min="0"
                      value={variant.price}
                      onChange={(value) =>
                        updateVariant(variant.localId, "price", value)
                      }
                    />
                    <Field
                      label="Compare / MRP"
                      type="number"
                      step="0.01"
                      min="0"
                      value={variant.compare_price}
                      onChange={(value) =>
                        updateVariant(variant.localId, "compare_price", value)
                      }
                    />
                    <Field
                      label="Stock"
                      type="number"
                      min="0"
                      value={variant.stock}
                      onChange={(value) =>
                        updateVariant(variant.localId, "stock", value)
                      }
                    />
                  </div>

                  <div className="editor-variant-foot">
                    <label className="check-control">
                      <input
                        type="checkbox"
                        checked={Boolean(variant.is_active)}
                        onChange={(event) =>
                          updateVariant(
                            variant.localId,
                            "is_active",
                            event.target.checked,
                          )
                        }
                      />
                      Available for sale
                    </label>
                    <div className="editor-variant-thumbnails">
                      {(variant.images || [])
                        .slice(0, 5)
                        .map((image, imageIndex) =>
                          image?.image_url ? (
                            <img
                              key={image.id || image.localId || imageIndex}
                              src={image.image_url}
                              alt="Variant"
                            />
                          ) : null,
                        )}
                    </div>
                    <button
                      type="button"
                      className="editor-btn primary"
                      onClick={() => saveVariant(variant)}
                      disabled={variantBusy === variant.localId}
                    >
                      <FaSave />{" "}
                      {variantBusy === variant.localId
                        ? "Saving…"
                        : "Save variant"}
                    </button>
                  </div>
                  {variant.dirty ? (
                    <div className="editor-dirty-note">Unsaved changes</div>
                  ) : null}
                </div>
              ))}
            </div>
          ) : (
            <div className="editor-empty-variants">
              <strong>No variants configured</strong>
              <span>
                Add a variant only when the product has multiple sellable
                combinations.
              </span>
              <button
                type="button"
                className="editor-btn secondary"
                onClick={addVariant}
              >
                <FaPlus /> Add first variant
              </button>
            </div>
          )}
        </section>

        <div className="editor-footer editor-sticky-footer">
          <button
            type="button"
            className="editor-btn secondary"
            onClick={() => navigate("/products")}
          >
            Cancel
          </button>
          <button
            type="submit"
            className="editor-btn primary"
            disabled={saving}
          >
            <FaSave /> {saving ? "Saving changes…" : "Save all changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
