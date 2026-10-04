import { Link } from "react-router-dom";
import Container from "../common/Container";
import SectionHeader from "../common/SectionHeader";

export default function Brands({ brands = [] }) {
  if (!brands.length) return null;
  return (
    <section className="cc-section">
      <Container>
        <SectionHeader
          title="Shop by brand"
          description="Discover brands already live on Clipcart."
        />
        <div className="cc-brand-grid">
          {brands.slice(0, 10).map((brand) => (
            <Link
              key={brand.id}
              className="cc-brand-card"
              to={`/products?brand=${encodeURIComponent(brand.slug)}`}
            >
              {brand.logo_url ? (
                <img src={brand.logo_url} alt="" loading="lazy" />
              ) : (
                <span className="cc-brand-mark">{brand.name.slice(0, 1)}</span>
              )}
              <span>{brand.name}</span>
            </Link>
          ))}
        </div>
      </Container>
    </section>
  );
}
