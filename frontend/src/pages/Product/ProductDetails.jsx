import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api from "../../services/api";
import { useCart } from "../../context/CartContext";

export default function ProductDetails() {
    const { id } = useParams();
    const { addToCart } = useCart();

    const [product, setProduct] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [quantity, setQuantity] = useState(1);
    const [selectedImage, setSelectedImage] = useState(0);
    const [adding, setAdding] = useState(false);

    useEffect(() => {
        async function loadProduct() {
            try {
                setLoading(true);
                const response = await api.get(`/products/${id}`);

                setProduct(
                    response.data?.data?.product ||
                    response.data?.data
                );
            } catch (err) {
                console.error(err);
                setError("Unable to load product.");
            } finally {
                setLoading(false);
            }
        }

        loadProduct();
    }, [id]);

    async function handleAddToCart() {
        if (!product) return;

        try {
            setAdding(true);

            await addToCart(
                {
                    ...product,
                    variant_id:
                        product.variant_id ||
                        product.variants?.[0]?.id ||
                        null,
                },
                quantity
            );
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.message ||
                "Unable to add product to cart."
            );
        } finally {
            setAdding(false);
        }
    }

    if (loading) {
        return (
            <section className="min-h-[70vh] flex items-center justify-center">
                <p className="text-xl text-gray-400">
                    Loading product...
                </p>
            </section>
        );
    }

    if (error || !product) {
        return (
            <section className="min-h-[70vh] flex flex-col items-center justify-center px-6">
                <h1 className="text-3xl font-black">
                    Product not found
                </h1>

                <p className="mt-3 text-gray-400">
                    {error || "This product is unavailable."}
                </p>

                <Link
                    to="/"
                    className="mt-6 rounded-xl bg-[#FFB703] px-6 py-3 font-bold text-black"
                >
                    Continue Shopping
                </Link>
            </section>
        );
    }

    const images = product.images || [];

    const imageUrls = images
        .map((image) =>
            typeof image === "string"
                ? image
                : image.image_url
        )
        .filter(Boolean);

    const currentImage =
        imageUrls[selectedImage] || null;

    const variants = product.variants || [];

    const selectedVariant =
        variants.length > 0
            ? variants[0]
            : null;

    const price = Number(
        selectedVariant?.price ??
        product.price ??
        0
    );

    const stock =
        selectedVariant?.stock ??
        product.stock ??
        0;

    const unavailable = stock <= 0;

    return (
        <section className="mx-auto max-w-[1500px] px-6 py-10">

            <div className="mb-6">
                <Link
                    to="/"
                    className="text-gray-400 hover:text-white"
                >
                    ← Back to Products
                </Link>
            </div>

            <div className="grid gap-10 lg:grid-cols-2">

                {/* Images */}
                <div>

                    <div className="flex min-h-[500px] items-center justify-center rounded-2xl bg-white p-8">

                        {currentImage ? (
                            <img
                                src={currentImage}
                                alt={product.name}
                                className="max-h-[500px] max-w-full object-contain"
                            />
                        ) : (
                            <div className="text-7xl">
                                📦
                            </div>
                        )}

                    </div>

                    {imageUrls.length > 1 && (
                        <div className="mt-4 flex gap-3 overflow-x-auto">

                            {imageUrls.map(
                                (image, index) => (
                                    <button
                                        key={image + index}
                                        type="button"
                                        onClick={() =>
                                            setSelectedImage(index)
                                        }
                                        className={`h-20 w-20 shrink-0 overflow-hidden rounded-lg border-2 bg-white ${
                                            selectedImage === index
                                                ? "border-[#FFB703]"
                                                : "border-transparent"
                                        }`}
                                    >
                                        <img
                                            src={image}
                                            alt={`${product.name} ${index + 1}`}
                                            className="h-full w-full object-contain"
                                        />
                                    </button>
                                )
                            )}

                        </div>
                    )}

                </div>

                {/* Product Information */}
                <div className="py-4">

                    <p className="mb-3 text-sm uppercase tracking-widest text-[#FFB703]">
                        Clipcart
                    </p>

                    <h1 className="text-4xl font-black md:text-5xl">
                        {product.name}
                    </h1>

                    {product.description && (
                        <p className="mt-6 leading-7 text-gray-400">
                            {product.description}
                        </p>
                    )}

                    <div className="my-8 border-t border-gray-700" />

                    <div className="text-4xl font-black text-[#FFB703]">
                        ₹{price.toFixed(0)}
                    </div>

                    <p className="mt-3 text-sm text-gray-400">
                        {unavailable
                            ? "Out of stock"
                            : `${stock} available`}
                    </p>

                    {variants.length > 0 && (
                        <div className="mt-8">
                            <h3 className="mb-3 font-bold">
                                Available Options
                            </h3>

                            <div className="flex flex-wrap gap-3">
                                {variants.map(
                                    (variant) => (
                                        <div
                                            key={variant.id}
                                            className="rounded-lg border border-gray-700 px-4 py-3"
                                        >
                                            {variant.name ||
                                                variant.title ||
                                                `Option ${variant.id}`}
                                        </div>
                                    )
                                )}
                            </div>
                        </div>
                    )}

                    <div className="mt-8 flex items-center gap-4">

                        <div className="flex items-center rounded-lg border border-gray-700">

                            <button
                                type="button"
                                onClick={() =>
                                    setQuantity(
                                        (q) =>
                                            Math.max(
                                                1,
                                                q - 1
                                            )
                                    )
                                }
                                className="px-5 py-3 text-xl"
                            >
                                −
                            </button>

                            <span className="px-5 font-bold">
                                {quantity}
                            </span>

                            <button
                                type="button"
                                onClick={() =>
                                    setQuantity(
                                        (q) =>
                                            Math.min(
                                                stock || 1,
                                                q + 1
                                            )
                                    )
                                }
                                className="px-5 py-3 text-xl"
                            >
                                +
                            </button>

                        </div>

                    </div>

                    <button
                        type="button"
                        onClick={handleAddToCart}
                        disabled={
                            unavailable || adding
                        }
                        className="mt-6 w-full rounded-xl bg-[#FFB703] py-4 text-lg font-black text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        {adding
                            ? "Adding..."
                            : unavailable
                                ? "Out of Stock"
                                : "Add to Cart"}
                    </button>

                    <Link
                        to="/cart"
                        className="mt-3 block w-full rounded-xl border border-gray-600 py-4 text-center font-bold hover:bg-[#232F3E]"
                    >
                        View Cart
                    </Link>

                </div>

            </div>

        </section>
    );
}