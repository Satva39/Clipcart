import ProductShelf from "./ProductShelf";

export default function TrendingSection({ products = [], loading = false }) {
  return (
    <ProductShelf
      title="Trending across Clipcart"
      description="Top 4 products by sold quantity across completed marketplace sales."
      products={products}
      loading={loading}
      to="/products?sort=popular"
    />
  );
}
