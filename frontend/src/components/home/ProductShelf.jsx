import { Link } from "react-router-dom";
import Container from "../common/Container";
import SectionHeader from "../common/SectionHeader";
import ProductCard from "../product/ProductCard";
import ProductSkeleton from "../product/ProductSkeleton";

export default function ProductShelf({
  title,
  description,
  products = [],
  loading = false,
  to = "/products",
}) {
  return (
    <section className="cc-section">
      <Container>
        <SectionHeader
          title={title}
          description={description}
          to={products.length ? to : undefined}
        />
        {loading ? (
          <ProductSkeleton count={4} />
        ) : products.length ? (
          <div className="cc-product-grid shelf">
            {products.slice(0, 4).map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        ) : (
          <div className="cc-slim-empty">
            <span>No products are available in this section yet.</span>
            <Link to="/products" className="cc-text-link">
              Browse the catalog →
            </Link>
          </div>
        )}
      </Container>
    </section>
  );
}
