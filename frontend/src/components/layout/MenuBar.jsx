import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { getStoreCategories } from "../../services/storeService";

export default function MenuBar() {
  const { data: categories = [] } = useQuery({
    queryKey: ["store", "categories"],
    queryFn: getStoreCategories,
    staleTime: 5 * 60 * 1000,
  });
  return (
    <nav className="cc-menu-bar" aria-label="Primary navigation">
      <div className="cc-container cc-menu-inner">
        <Link to="/products" className="cc-menu-link strong">
          All
        </Link>
        <Link to="/products?discount=true" className="cc-menu-link">
          Deals
        </Link>
        <Link to="/products?sort=newest" className="cc-menu-link">
          New arrivals
        </Link>
        {categories.slice(0, 9).map((category) => (
          <Link
            key={category.id}
            to={`/products?category=${encodeURIComponent(category.slug)}`}
            className="cc-menu-link"
          >
            {category.name}
          </Link>
        ))}
      </div>
    </nav>
  );
}
