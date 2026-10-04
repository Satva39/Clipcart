import { FiArrowUpRight } from "react-icons/fi";
import { Link } from "react-router-dom";
import Container from "../common/Container";
import SectionHeader from "../common/SectionHeader";

export default function CategoryDiscovery({ categories = [] }) {
  if (!categories.length) return null;
  return (
    <section className="cc-section tinted">
      <Container>
        <SectionHeader
          title="Browse categories"
          description="Start with a category and narrow the catalog from there."
        />
        <div className="cc-category-grid">
          {categories.slice(0, 10).map((category) => (
            <Link
              key={category.id}
              className="cc-category-card"
              to={`/products?category=${encodeURIComponent(category.slug)}`}
            >
              <span>{category.name}</span>
              <FiArrowUpRight />
            </Link>
          ))}
        </div>
      </Container>
    </section>
  );
}
