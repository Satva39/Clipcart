import { Link } from "react-router-dom";
import useProducts from "../../hooks/useProducts";

function getImage(product) {
  const image = product?.images?.[0];

  if (typeof image === "string") {
    return image;
  }

  return image?.image_url ?? image?.url ?? product?.image_url ?? null;
}

export default function RelatedProducts({ currentProduct }) {
  const { products, loading } = useProducts();

  if (loading) {
    return (
      <section className="mt-12">
        <h2 className="mb-6 text-3xl font-black">Similar Products</h2>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <div
              key={item}
              className="h-80 animate-pulse rounded-2xl bg-[#232F3E]"
            />
          ))}
        </div>
      </section>
    );
  }

  const relatedProducts = products
    .filter((product) => product.id !== currentProduct?.id)
    .filter((product) => {
      if (!currentProduct?.category || !product.category) {
        return true;
      }

      return (
        String(product.category).toLowerCase() ===
        String(currentProduct.category).toLowerCase()
      );
    })
    .slice(0, 4);

  if (!relatedProducts.length) {
    return null;
  }

  return (
    <section className="mt-12">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-3xl font-black">Similar Products</h2>

        <Link
          to="/search"
          className="text-sm font-bold text-[#FFB703] hover:underline"
        >
          View All
        </Link>
      </div>

      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {relatedProducts.map((product) => {
          const image = getImage(product);

          return (
            <Link
              key={product.id}
              to={`/product/${product.id}`}
              className="group overflow-hidden rounded-2xl bg-[#232F3E] transition hover:-translate-y-1 hover:ring-2 hover:ring-[#FFB703]"
            >
              <div className="relative flex h-56 items-center justify-center bg-[#131921] p-5">
                {image ? (
                  <img
                    loading="lazy"
                    decoding="async"
                    src={image}
                    alt={product.name}
                    className="h-full w-full object-contain transition duration-300 group-hover:scale-105"
                  />
                ) : (
                  <span className="text-5xl">📦</span>
                )}
              </div>

              <div className="p-5">
                <p className="text-xs uppercase tracking-wider text-[#FFB703]">
                  {product.category || "Product"}
                </p>

                <h3 className="mt-2 line-clamp-2 text-lg font-bold">
                  {product.name}
                </h3>

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-2xl font-black text-[#FFB703]">
                    ₹{Number(product.price || 0).toLocaleString("en-IN")}
                  </span>

                  <span className="rounded-lg bg-[#FFB703] px-3 py-2 text-sm font-bold text-black">
                    View
                  </span>
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
