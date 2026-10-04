import { memo } from "react";
import ProductCard from "./ProductCard";

function ProductGrid({ products = [] }) {
  return (
    <div className="cc-product-grid">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}

export default memo(ProductGrid);
