import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import useProducts from "../../hooks/useProducts";

export default function Product() {
    const { products, loading } = useProducts();
    const [searchParams] = useSearchParams();

    const initialCategory = searchParams.get("category") || "All";

    const [search, setSearch] = useState("");
    const [category, setCategory] = useState(initialCategory);
    const [sort, setSort] = useState("default");

    const categories = useMemo(() => {
        return [
            "All",
            ...new Set(
                products
                    .map((product) => product.category)
                    .filter(Boolean)
            ),
        ];
    }, [products]);

    const filteredProducts = useMemo(() => {
        let result = products.filter((product) => {
            const query = search.toLowerCase();

            const matchesSearch =
                product.name?.toLowerCase().includes(query) ||
                product.brand?.toLowerCase().includes(query);

            const matchesCategory =
                category === "All" ||
                product.category === category;

            return matchesSearch && matchesCategory;
        });

        if (sort === "price-low") {
            result.sort(
                (a, b) => Number(a.price || 0) - Number(b.price || 0)
            );
        }

        if (sort === "price-high") {
            result.sort(
                (a, b) => Number(b.price || 0) - Number(a.price || 0)
            );
        }

        if (sort === "name") {
            result.sort((a, b) =>
                (a.name || "").localeCompare(b.name || "")
            );
        }

        return result;
    }, [products, search, category, sort]);

    return (
        <section className="mx-auto max-w-[1600px] px-6 py-10">

            <h1 className="mb-8 text-4xl font-black">
                All Products
            </h1>

            <div className="mb-8 grid gap-4 md:grid-cols-[1fr_220px_180px]">

                <input
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    placeholder="Search products..."
                    className="rounded-xl bg-[#232F3E] px-5 py-4 outline-none"
                />

                <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="rounded-xl bg-[#232F3E] px-5 py-4 outline-none"
                >
                    {categories.map((item) => (
                        <option key={item} value={item}>
                            {item}
                        </option>
                    ))}
                </select>

                <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value)}
                    className="rounded-xl bg-[#232F3E] px-5 py-4 outline-none"
                >
                    <option value="default">Sort By</option>
                    <option value="price-low">Price: Low to High</option>
                    <option value="price-high">Price: High to Low</option>
                    <option value="name">Name</option>
                </select>

            </div>

            {loading ? (
                <div className="py-24 text-center">
                    Loading products...
                </div>
            ) : (
                <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                    {filteredProducts.map((product) => (
                        <Link
                            key={product.id}
                            to={`/product/${product.id}`}
                        >
                            <div className="rounded-2xl bg-[#232F3E] p-5">
                                <div className="flex h-64 items-center justify-center bg-[#131921]">
                                    <span className="text-4xl font-black">
                                        Clipcart
                                    </span>
                                </div>

                                <p className="mt-4 text-xs text-[#FFB703]">
                                    {product.category}
                                </p>

                                <h2 className="mt-2 text-xl font-bold">
                                    {product.name}
                                </h2>

                                <p className="mt-3 text-2xl font-black text-[#FFB703]">
                                    ₹{Number(product.price || 0).toFixed(0)}
                                </p>
                            </div>
                        </Link>
                    ))}
                </div>
            )}

        </section>
    );
}