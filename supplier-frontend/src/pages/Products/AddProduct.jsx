import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { FaArrowLeft, FaImage, FaPlus, FaSave, FaTrash } from "react-icons/fa";
import {
  createBrand,
  createCategory,
  createProductVariants,
  createSupplierProduct,
  getBrands,
  getCategories,
  uploadProductImages,
} from "../../services/productService";
import "../../styles/supplier-pages.css";
import "./add-product.css";

const newId = (prefix = "item") =>
  `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;

const emptyVariant = (price = "") => ({
  localId: newId("variant"),
  options: [{ name: "", value: "" }],
  sku: "",
  price,
  compare_price: "",
  stock: "0",
  is_active: true,
  images: [],
});

function Field({
  label,
  value,
  set,
  type = "text",
  required = false,
  disabled = false,
  placeholder,
}) {
  return (
    <label className="form-label">
      <span>{label}</span>
      <input
        className="form-control"
        type={type}
        value={value ?? ""}
        onChange={(event) => set(event.target.value)}
        required={required}
        disabled={disabled}
        placeholder={placeholder}
      />
    </label>
  );
}

function VariantCard({
  variant,
  index,
  onChange,
  onOptionChange,
  onAddOption,
  onRemoveOption,
  onRemove,
}) {
  const imageInputRef = useRef(null);

  return (
    <article className="product-variant-card">
      <div className="product-variant-head">
        <div>
          <span className="product-variant-number">Variant {index + 1}</span>
          <strong>
            {variant.options
              .map((option) => `${option.name}: ${option.value}`)
              .filter(Boolean)
              .join(" · ") || "New variant"}
          </strong>
        </div>
        <button
          type="button"
          className="editor-icon-btn danger"
          onClick={onRemove}
          title="Remove variant"
        >
          <FaTrash />
        </button>
      </div>

      <div className="product-variant-options">
        {variant.options.map((option, optionIndex) => (
          <div
            className="product-option-row"
            key={`${variant.localId}-${optionIndex}`}
          >
            <input
              className="form-control"
              placeholder="Option name e.g. Color"
              value={option.name}
              onChange={(event) =>
                onOptionChange(
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
                onOptionChange(
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
              onClick={() => onRemoveOption(variant.localId, optionIndex)}
              title="Remove option"
            >
              ×
            </button>
          </div>
        ))}
        <button
          type="button"
          className="editor-text-btn"
          onClick={() => onAddOption(variant.localId)}
        >
          <FaPlus /> Add option
        </button>
      </div>

      <div className="form-grid-4 product-variant-fields">
        <Field
          label="SKU"
          value={variant.sku}
          set={(value) => onChange(variant.localId, "sku", value)}
          placeholder="Auto-generated if blank"
        />
        <Field
          label="Selling price"
          type="number"
          value={variant.price}
          set={(value) => onChange(variant.localId, "price", value)}
          placeholder="0.00"
        />
        <Field
          label="Compare / MRP"
          type="number"
          value={variant.compare_price}
          set={(value) => onChange(variant.localId, "compare_price", value)}
          placeholder="Optional"
        />
        <Field
          label="Stock"
          type="number"
          value={variant.stock}
          set={(value) => onChange(variant.localId, "stock", value)}
          placeholder="0"
        />
      </div>

      <div className="product-variant-bottom">
        <label className="check-control">
          <input
            type="checkbox"
            checked={Boolean(variant.is_active)}
            onChange={(event) =>
              onChange(variant.localId, "is_active", event.target.checked)
            }
          />
          Available for sale
        </label>

        <div className="product-variant-images">
          {(variant.images || []).map((image) =>
            image?.preview ? (
              <img
                key={image.localId}
                src={image.preview}
                alt="Variant preview"
              />
            ) : null,
          )}
          {(variant.images || []).length ? (
            <span>
              {variant.images.length} image
              {variant.images.length === 1 ? "" : "s"}
            </span>
          ) : null}
        </div>

        <button
          type="button"
          className="editor-btn secondary small"
          onClick={() => imageInputRef.current?.click()}
        >
          <FaImage /> Add variant images
        </button>
        <input
          ref={imageInputRef}
          className="supplier-file-input supplier-file-input-native"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          onChange={(event) => {
            const files = Array.from(event.target.files || []);
            event.target.value = "";
            if (!files.length) return;
            const next = files.map((file) => ({
              localId: newId("image"),
              file,
              preview: URL.createObjectURL(file),
              name: file.name,
            }));
            onChange(variant.localId, "images", [
              ...(variant.images || []),
              ...next,
            ]);
          }}
        />
      </div>
    </article>
  );
}

export default function AddProduct() {
  const navigate = useNavigate();
  const productImageInputRef = useRef(null);
  const [form, setForm] = useState({
    name: "",
    brand_id: "",
    category_id: "",
    description: "",
    highlights: "",
    specifications: "",
    price: "",
    compare_price: "",
    stock: "0",
    low_stock_threshold: "5",
    shipping_weight_kg: "",
    shipping_length_cm: "",
    shipping_width_cm: "",
    shipping_height_cm: "",
    sku: "",
    status: "ACTIVE",
    is_featured: false,
  });
  const [categories, setCategories] = useState([]);
  const [brands, setBrands] = useState([]);
  const [options, setOptions] = useState([
    { id: newId("option"), name: "", values: "" },
  ]);
  const [variants, setVariants] = useState([]);
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    Promise.all([getCategories(), getBrands()])
      .then(([categoryData, brandData]) => {
        setCategories(categoryData || []);
        setBrands(brandData || []);
      })
      .catch((err) => {
        setError(
          err?.response?.data?.message ||
            "Unable to load categories and brands.",
        );
      });
  }, []);

  const update = (key, value) =>
    setForm((current) => ({ ...current, [key]: value }));

  const totalVariantStock = useMemo(
    () =>
      variants.reduce(
        (sum, variant) => sum + Math.max(0, Number(variant.stock) || 0),
        0,
      ),
    [variants],
  );

  function addOption() {
    setOptions((current) => [
      ...current,
      { id: newId("option"), name: "", values: "" },
    ]);
  }

  function updateOption(optionId, key, value) {
    setOptions((current) =>
      current.map((option) =>
        option.id === optionId ? { ...option, [key]: value } : option,
      ),
    );
  }

  function removeOption(optionId) {
    setOptions((current) => current.filter((option) => option.id !== optionId));
  }

  function generateVariants() {
    const definitions = options
      .map((option) => ({
        name: option.name.trim(),
        values: option.values
          .split(",")
          .map((value) => value.trim())
          .filter(Boolean),
      }))
      .filter((option) => option.name && option.values.length);

    if (!definitions.length) {
      setError(
        "Add at least one option name and enter its values separated by commas.",
      );
      return;
    }

    const combinations = definitions.reduce(
      (accumulator, definition) =>
        accumulator.flatMap((prefix) =>
          definition.values.map((value) => [
            ...prefix,
            { name: definition.name, value },
          ]),
        ),
      [[]],
    );

    const seen = new Set();
    const generated = combinations
      .filter((combination) => {
        const key = JSON.stringify(
          [...combination].sort((a, b) => a.name.localeCompare(b.name)),
        );
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
      })
      .map((combination) => ({
        ...emptyVariant(form.price),
        options: combination,
      }));

    setVariants(generated);
    setError("");
  }

  function addBlankVariant() {
    setVariants((current) => [...current, emptyVariant(form.price)]);
  }

  function updateVariant(localId, key, value) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId ? { ...variant, [key]: value } : variant,
      ),
    );
  }

  function updateVariantOption(localId, optionIndex, key, value) {
    setVariants((current) =>
      current.map((variant) =>
        variant.localId === localId
          ? {
              ...variant,
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
              options: variant.options.filter(
                (_, index) => index !== optionIndex,
              ),
            }
          : variant,
      ),
    );
  }

  function removeVariant(localId) {
    setVariants((current) =>
      current.filter((variant) => variant.localId !== localId),
    );
  }

  async function addMaster(type) {
    const name = window.prompt(`New ${type} name`);
    if (!name?.trim()) return;
    try {
      const response =
        type === "category"
          ? await createCategory(name.trim())
          : await createBrand(name.trim());
      const item =
        response?.data || response?.category || response?.brand || response;
      if (!item?.id) return;
      if (type === "category") {
        setCategories((current) => [...current, item]);
        update("category_id", String(item.id));
      } else {
        setBrands((current) => [...current, item]);
        update("brand_id", String(item.id));
      }
    } catch (err) {
      setError(err?.response?.data?.message || `Unable to create ${type}.`);
    }
  }

  function addSelectedImages(files) {
    const selected = Array.from(files || []);
    if (!selected.length) return;
    setImages((current) => {
      const existing = new Set(
        current.map(
          ({ file }) => `${file.name}-${file.lastModified}-${file.size}`,
        ),
      );
      const next = selected
        .filter(
          (file) =>
            !existing.has(`${file.name}-${file.lastModified}-${file.size}`),
        )
        .map((file) => ({
          file,
          preview: URL.createObjectURL(file),
        }));
      return [...current, ...next];
    });
  }

  async function submit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");
    setMessage("");

    try {
      if (!form.name.trim()) throw new Error("Product name is required.");
      if (!form.category_id) throw new Error("Select a category.");
      if (!form.description.trim())
        throw new Error("Product description is required.");
      if (!Number.isFinite(Number(form.price)) || Number(form.price) < 0) {
        throw new Error("Selling price must be a valid non-negative number.");
      }

      const product = await createSupplierProduct({
        name: form.name.trim(),
        brand_id: form.brand_id ? Number(form.brand_id) : null,
        category_id: Number(form.category_id),
        description: form.description.trim(),
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
        price: Number(form.price),
        compare_price:
          form.compare_price === "" ? null : Number(form.compare_price),
        stock: variants.length ? totalVariantStock : Number(form.stock || 0),
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
        sku: form.sku.trim() || `CLP-${Date.now()}`,
        status: form.status,
        is_featured: Boolean(form.is_featured),
      });

      const productId = product?.data?.id || product?.id;
      if (!productId)
        throw new Error("Product created but the server did not return an ID.");

      if (images.length) {
        await uploadProductImages(
          productId,
          images.map((file) => ({ file })),
        );
      }

      if (variants.length) {
        const createdVariants = await createProductVariants(
          productId,
          variants.map((variant) => ({
            options: variant.options,
            sku:
              variant.sku.trim() ||
              `CLP-V-${Date.now()}-${Math.random().toString(16).slice(2, 8)}`,
            price: Number(variant.price || form.price || 0),
            compare_price:
              variant.compare_price === ""
                ? null
                : Number(variant.compare_price),
            stock: Number(variant.stock || 0),
            is_active: Boolean(variant.is_active),
          })),
        );

        for (
          let index = 0;
          index < (createdVariants || []).length;
          index += 1
        ) {
          const variantImages = variants[index]?.images || [];
          if (variantImages.length && createdVariants[index]?.id) {
            await uploadProductImages(
              productId,
              variantImages.map((image) => ({ file: image.file })),
              createdVariants[index].id,
            );
          }
        }
      }

      setMessage("Product created successfully. Opening the edit workspace…");
      window.setTimeout(() => navigate(`/products/${productId}/edit`), 500);
    } catch (err) {
      setError(
        err?.response?.data?.message ||
          err?.message ||
          "Unable to create product.",
      );
    } finally {
      setLoading(false);
    }
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
              <h2>Add product</h2>
              <p>
                Start with the essentials. Add variants and images only when you
                need them.
              </p>
            </div>
          </div>
        </div>
      </div>

      {error ? <div className="notice error">{error}</div> : null}
      {message ? <div className="notice success">{message}</div> : null}

      <form className="product-editor" onSubmit={submit}>
        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">1. Basic information</h3>
              <p className="panel-subtitle">
                The information customers will see on the product page.
              </p>
            </div>
          </div>
          <div className="form-grid-2">
            <Field
              label="Product name"
              value={form.name}
              set={(value) => update("name", value)}
              required
              placeholder="e.g. Unique Calendar"
            />
            <Field
              label="Product SKU"
              value={form.sku}
              set={(value) => update("sku", value)}
              placeholder="Optional — generated if blank"
            />
          </div>
          <label className="form-label">
            <span>Description</span>
            <textarea
              className="form-control form-textarea editor-textarea-lg"
              value={form.description}
              onChange={(event) => update("description", event.target.value)}
              required
              placeholder="Describe the product clearly."
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
                placeholder="Premium paper\nDurable stand"
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
              <h3 className="panel-title">2. Catalog & pricing</h3>
              <p className="panel-subtitle">
                Choose where the product belongs and set its price.
              </p>
            </div>
            <div className="editor-inline-actions">
              <button
                type="button"
                className="editor-btn secondary small"
                onClick={() => addMaster("category")}
              >
                + Category
              </button>
              <button
                type="button"
                className="editor-btn secondary small"
                onClick={() => addMaster("brand")}
              >
                + Brand
              </button>
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
              value={form.price}
              set={(value) => update("price", value)}
              required
              placeholder="0.00"
            />
            <Field
              label="Compare / MRP"
              type="number"
              value={form.compare_price}
              set={(value) => update("compare_price", value)}
              placeholder="Optional"
            />
            <Field
              label="Low-stock threshold"
              type="number"
              value={form.low_stock_threshold}
              set={(value) => update("low_stock_threshold", value)}
              placeholder="5"
            />
          </div>
          <div className="form-grid-2">
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
              Featured product
            </label>
          </div>
        </section>

        <section className="panel form-card editor-card">
          <div className="editor-section-head">
            <div>
              <h3 className="panel-title">3. Shipping package</h3>
              <p className="panel-subtitle">
                Enter the real packed weight and dimensions used for courier
                pickup.
              </p>
            </div>
          </div>
          <div className="form-grid-4">
            <Field
              label="Weight (kg)"
              type="number"
              value={form.shipping_weight_kg}
              set={(value) => update("shipping_weight_kg", value)}
              placeholder="e.g. 0.50"
            />
            <Field
              label="Length (cm)"
              type="number"
              value={form.shipping_length_cm}
              set={(value) => update("shipping_length_cm", value)}
              placeholder="e.g. 20"
            />
            <Field
              label="Width (cm)"
              type="number"
              value={form.shipping_width_cm}
              set={(value) => update("shipping_width_cm", value)}
              placeholder="e.g. 15"
            />
            <Field
              label="Height (cm)"
              type="number"
              value={form.shipping_height_cm}
              set={(value) => update("shipping_height_cm", value)}
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
              <h3 className="panel-title">4. Product images</h3>
              <p className="panel-subtitle">
                Select one or more JPG, PNG or WebP files.
              </p>
            </div>
            <button
              type="button"
              className="editor-btn primary"
              onClick={() => productImageInputRef.current?.click()}
            >
              <FaImage /> Choose images
            </button>
            <input
              ref={productImageInputRef}
              className="supplier-file-input supplier-file-input-native"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={(event) => {
                const files = Array.from(event.target.files || []);
                event.target.value = "";
                addSelectedImages(files);
              }}
            />
          </div>
          {images.length ? (
            <div className="editor-new-image-grid">
              {images.map((entry) => (
                <div
                  className="editor-new-image"
                  key={`${entry.file.name}-${entry.file.lastModified}-${entry.file.size}`}
                >
                  <div className="editor-new-image-preview">
                    <img
                      src={entry.preview}
                      alt={entry.file.name}
                      loading="lazy"
                      decoding="async"
                    />
                  </div>
                  <span title={entry.file.name}>{entry.file.name}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="editor-empty-media">
              <FaImage />
              <div>
                <strong>No images selected</strong>
                <span>
                  Product images make the listing easier to understand.
                </span>
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
              <h3 className="panel-title">
                4. Variants <span className="optional-label">Optional</span>
              </h3>
              <p className="panel-subtitle">
                Use variants for different colors, sizes, storage options or
                other sellable combinations.
              </p>
            </div>
            <div className="editor-inline-actions">
              <button
                type="button"
                className="editor-btn secondary"
                onClick={addOption}
              >
                <FaPlus /> Add option
              </button>
              <button
                type="button"
                className="editor-btn primary"
                onClick={generateVariants}
              >
                Generate combinations
              </button>
            </div>
          </div>

          <div className="product-option-builder">
            {options.map((option) => (
              <div className="product-option-definition" key={option.id}>
                <input
                  className="form-control"
                  placeholder="Option name e.g. Color"
                  value={option.name}
                  onChange={(event) =>
                    updateOption(option.id, "name", event.target.value)
                  }
                />
                <input
                  className="form-control"
                  placeholder="Values separated by commas e.g. Green, Blue"
                  value={option.values}
                  onChange={(event) =>
                    updateOption(option.id, "values", event.target.value)
                  }
                />
                <button
                  type="button"
                  className="editor-icon-btn subtle"
                  onClick={() => removeOption(option.id)}
                  disabled={options.length <= 1}
                  title="Remove option"
                >
                  <FaTrash />
                </button>
              </div>
            ))}
          </div>

          {variants.length ? (
            <div className="editor-variant-list">
              {variants.map((variant, index) => (
                <VariantCard
                  key={variant.localId}
                  variant={variant}
                  index={index}
                  onChange={updateVariant}
                  onOptionChange={updateVariantOption}
                  onAddOption={addVariantOption}
                  onRemoveOption={removeVariantOption}
                  onRemove={() => removeVariant(variant.localId)}
                />
              ))}
            </div>
          ) : (
            <div className="editor-empty-variants">
              <strong>This product has no variants</strong>
              <span>
                You can sell it as a single product, or create variants above.
              </span>
              <button
                type="button"
                className="editor-btn secondary"
                onClick={addBlankVariant}
              >
                <FaPlus /> Add a variant manually
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
          <button className="editor-btn primary" disabled={loading}>
            <FaSave /> {loading ? "Creating product…" : "Create product"}
          </button>
        </div>
      </form>
    </div>
  );
}
