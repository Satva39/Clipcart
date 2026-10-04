import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { FiFilter, FiSearch, FiSliders, FiX } from "react-icons/fi";
import { useSearchParams } from "react-router-dom";
import {
  getStoreBrands,
  getStoreCategories,
  searchStore,
} from "../../services/storeService";
import { getApiMessage } from "../../utils/apiError";
import Container from "../../components/common/Container";
import ProductGrid from "../../components/product/ProductGrid";
import ProductSkeleton from "../../components/product/ProductSkeleton";
import { ErrorState, EmptyState } from "../../components/common/AsyncState";

const SORTS = [
  ["relevance", "Relevance"],
  ["price_asc", "Price: low to high"],
  ["price_desc", "Price: high to low"],
  ["newest", "Newest"],
  ["popular", "Most popular"],
  ["rating", "Customer rating"],
  ["discount", "Discount"],
];

function boolParam(value) {
  return value === "true";
}

function FilterPanel({
  params,
  setParam,
  categories,
  brands,
  compact = false,
}) {
  const setAndPage = (key, value) => {
    setParam(key, value, true);
  };

  return (
    <div className={`cc-filter-panel${compact ? " compact" : ""}`}>
      <div className="cc-filter-group">
        <label htmlFor="category-filter">Category</label>
        <select
          id="category-filter"
          value={params.category}
          onChange={(e) => setAndPage("category", e.target.value)}
        >
          <option value="">All categories</option>
          {categories.map((category) => (
            <option key={category.id} value={category.slug}>
              {category.name}
            </option>
          ))}
        </select>
      </div>

      <div className="cc-filter-group">
        <label htmlFor="brand-filter">Brand</label>
        <select
          id="brand-filter"
          value={params.brand}
          onChange={(e) => setAndPage("brand", e.target.value)}
        >
          <option value="">All brands</option>
          {brands.map((brand) => (
            <option key={brand.id} value={brand.slug}>
              {brand.name}
            </option>
          ))}
        </select>
      </div>

      <div className="cc-filter-group">
        <span className="cc-filter-label">Price</span>
        <div className="cc-price-inputs">
          <input
            inputMode="numeric"
            type="number"
            min="0"
            value={params.min_price}
            onChange={(e) => setAndPage("min_price", e.target.value)}
            placeholder="Min"
            aria-label="Minimum price"
          />
          <input
            inputMode="numeric"
            type="number"
            min="0"
            value={params.max_price}
            onChange={(e) => setAndPage("max_price", e.target.value)}
            placeholder="Max"
            aria-label="Maximum price"
          />
        </div>
      </div>

      <div className="cc-filter-group">
        <span className="cc-filter-label">Customer rating</span>
        {[4, 3, 2].map((rating) => (
          <label className="cc-check-row" key={rating}>
            <input
              type="radio"
              name="rating"
              checked={String(params.min_rating) === String(rating)}
              onChange={() => setAndPage("min_rating", String(rating))}
            />
            <span>{rating}★ & above</span>
          </label>
        ))}
        {params.min_rating ? (
          <button
            type="button"
            className="cc-filter-clear"
            onClick={() => setAndPage("min_rating", "")}
          >
            Clear rating
          </button>
        ) : null}
      </div>

      <div className="cc-filter-group">
        <span className="cc-filter-label">Availability</span>
        <label className="cc-check-row">
          <input
            type="checkbox"
            checked={boolParam(params.in_stock)}
            onChange={(e) =>
              setAndPage("in_stock", e.target.checked ? "true" : "")
            }
          />
          <span>In stock only</span>
        </label>
      </div>

      <div className="cc-filter-group">
        <span className="cc-filter-label">Discount</span>
        <label className="cc-check-row">
          <input
            type="checkbox"
            checked={boolParam(params.discount)}
            onChange={(e) =>
              setAndPage("discount", e.target.checked ? "true" : "")
            }
          />
          <span>Any discount</span>
        </label>
        <select
          value={params.discount_min}
          onChange={(e) => setAndPage("discount_min", e.target.value)}
          aria-label="Minimum discount"
        >
          <option value="">Minimum discount</option>
          <option value="10">10%+</option>
          <option value="20">20%+</option>
          <option value="30">30%+</option>
          <option value="50">50%+</option>
        </select>
      </div>

      <div className="cc-filter-group">
        <span className="cc-filter-label">Variants</span>
        <label className="cc-check-row">
          <input
            type="checkbox"
            checked={boolParam(params.has_variants)}
            onChange={(e) =>
              setAndPage("has_variants", e.target.checked ? "true" : "")
            }
          />
          <span>Has variants</span>
        </label>
      </div>
    </div>
  );
}

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [draftSearch, setDraftSearch] = useState(searchParams.get("q") || "");
  const [mobileFilters, setMobileFilters] = useState(false);

  const params = useMemo(
    () => ({
      q: searchParams.get("q") || "",
      category: searchParams.get("category") || "",
      brand: searchParams.get("brand") || "",
      min_price: searchParams.get("min_price") || "",
      max_price: searchParams.get("max_price") || "",
      min_rating: searchParams.get("min_rating") || "",
      in_stock: searchParams.get("in_stock") || "",
      discount: searchParams.get("discount") || "",
      discount_min: searchParams.get("discount_min") || "",
      has_variants: searchParams.get("has_variants") || "",
      sort: searchParams.get("sort") || "relevance",
      page: Number(searchParams.get("page") || 1),
    }),
    [searchParams],
  );

  const categoryQuery = useQuery({
    queryKey: ["catalog", "categories"],
    queryFn: getStoreCategories,
    staleTime: 5 * 60 * 1000,
  });
  const brandQuery = useQuery({
    queryKey: ["catalog", "brands"],
    queryFn: getStoreBrands,
    staleTime: 5 * 60 * 1000,
  });

  const query = useQuery({
    queryKey: ["store-search", params],
    queryFn: () => searchStore({ ...params, limit: 24 }),
  });

  // The URL is the source of truth when navigation happens outside this form.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setDraftSearch(params.q), [params.q]);

  const products = query.data?.products || [];
  const pagination = query.data?.pagination || {};
  const categories = categoryQuery.data || [];
  const brands = brandQuery.data || [];
  const hasFilters = Boolean(
    params.category ||
    params.brand ||
    params.min_price ||
    params.max_price ||
    params.min_rating ||
    params.in_stock ||
    params.discount ||
    params.discount_min ||
    params.has_variants,
  );

  function setParam(key, value, resetPage = false) {
    const next = new URLSearchParams(searchParams);
    if (value === "" || value == null) next.delete(key);
    else next.set(key, value);
    if (resetPage && key !== "page") next.set("page", "1");
    setSearchParams(next, { replace: true });
  }

  function submitSearch(event) {
    event.preventDefault();
    const next = new URLSearchParams(searchParams);
    if (draftSearch.trim()) next.set("q", draftSearch.trim());
    else next.delete("q");
    next.set("page", "1");
    setSearchParams(next, { replace: true });
  }

  function clearAll() {
    const next = new URLSearchParams();
    if (params.q) next.set("q", params.q);
    setSearchParams(next, { replace: true });
  }

  const heading = params.q
    ? `Results for “${params.q}”`
    : params.category
      ? `Products in ${params.category.replace(/-/g, " ")}`
      : "Shop all products";

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-search-head">
          <div>
            <span className="cc-eyebrow">Clipcart marketplace</span>
            <h1>{heading}</h1>
            <p>
              {pagination.total != null
                ? `${pagination.total.toLocaleString("en-IN")} products`
                : "Browse the live catalog"}
            </p>
          </div>
          <form className="cc-inline-search" onSubmit={submitSearch}>
            <FiSearch aria-hidden="true" />
            <input
              value={draftSearch}
              onChange={(e) => setDraftSearch(e.target.value)}
              placeholder="Search products, brands or categories"
              aria-label="Search products"
            />
            <button type="submit" className="cc-btn primary">
              Search
            </button>
          </form>
        </div>

        <div className="cc-discovery-toolbar">
          <button
            type="button"
            className="cc-filter-toggle"
            onClick={() => setMobileFilters(true)}
          >
            <FiFilter /> Filters {hasFilters ? "•" : ""}
          </button>
          <div className="cc-sort">
            <FiSliders />
            <label htmlFor="sort">Sort</label>
            <select
              id="sort"
              value={params.sort}
              onChange={(e) => setParam("sort", e.target.value)}
            >
              {SORTS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="cc-search-layout">
          <aside className="cc-filter-sidebar" aria-label="Product filters">
            <div className="cc-filter-heading">
              <strong>Filters</strong>
              {hasFilters ? (
                <button type="button" onClick={clearAll}>
                  Clear all
                </button>
              ) : null}
            </div>
            <FilterPanel
              params={params}
              setParam={setParam}
              categories={categories}
              brands={brands}
            />
          </aside>

          <main className="cc-results">
            {query.isError ? (
              <ErrorState
                message={getApiMessage(
                  query.error,
                  "We couldn't load these products.",
                )}
                onRetry={() => query.refetch()}
              />
            ) : query.isLoading ? (
              <ProductSkeleton count={8} />
            ) : !products.length ? (
              <EmptyState
                title="No products found"
                message="Try a broader search or remove one of the filters."
                action={
                  <button
                    type="button"
                    className="cc-btn secondary"
                    onClick={clearAll}
                  >
                    Clear filters
                  </button>
                }
              />
            ) : (
              <ProductGrid products={products} />
            )}

            {pagination.pages > 1 ? (
              <nav className="cc-pagination" aria-label="Product pagination">
                <button
                  type="button"
                  disabled={!pagination.has_prev}
                  onClick={() => setParam("page", String(params.page - 1))}
                >
                  Previous
                </button>
                <span>
                  Page {pagination.page} of {pagination.pages}
                </span>
                <button
                  type="button"
                  disabled={!pagination.has_next}
                  onClick={() => setParam("page", String(params.page + 1))}
                >
                  Next
                </button>
              </nav>
            ) : null}
          </main>
        </div>
      </Container>

      {mobileFilters ? (
        <div
          className="cc-filter-overlay"
          role="dialog"
          aria-modal="true"
          aria-label="Filters"
        >
          <div className="cc-filter-drawer">
            <div className="cc-filter-heading">
              <strong>Filters</strong>
              <button
                type="button"
                className="cc-icon-btn"
                onClick={() => setMobileFilters(false)}
                aria-label="Close filters"
              >
                <FiX />
              </button>
            </div>
            <FilterPanel
              params={params}
              setParam={setParam}
              categories={categories}
              brands={brands}
              compact
            />
            <button
              type="button"
              className="cc-btn primary full"
              onClick={() => setMobileFilters(false)}
            >
              Show results
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
