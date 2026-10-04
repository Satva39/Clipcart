import { useState } from "react";
import { getRecentlyViewed } from "../../utils/recentlyViewed";
import Container from "../common/Container";
import SectionHeader from "../common/SectionHeader";
import ProductCard from "../product/ProductCard";

export default function RecentlyViewed() {
  const [items] = useState(getRecentlyViewed);

  if (!items.length) return null;

  return (
    <section className="cc-section">
      <Container>
        <SectionHeader
          title="Recently viewed"
          description="Pick up where you left off."
        />
        <div className="cc-product-grid shelf">
          {items.slice(0, 4).map((product) => (
            <ProductCard key={product.id} product={product} />
          ))}
        </div>
      </Container>
    </section>
  );
}
