import ProductShelf from "./ProductShelf";

export default function FeaturedProducts({ products = [], loading = false }) {
  return (
    <ProductShelf
      title="Featured products"
      description="Products selected as featured by the marketplace catalog."
      products={products}
      loading={loading}
    />
  );
}
