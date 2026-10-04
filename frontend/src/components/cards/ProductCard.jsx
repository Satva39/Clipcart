import { Link } from "react-router-dom";

export default function ProductCard({ product }) {

    return (

        <Link
            to={`/product/${product.id}`}
            className="block rounded-2xl bg-[#232F3E] overflow-hidden transition duration-300 hover:scale-[1.02]"
        >

            <div className="flex h-64 items-center justify-center bg-[#131921] text-5xl font-black">

                Clipcart

            </div>

            <div className="p-5">

                <h3 className="text-xl font-bold">

                    {product.name}

                </h3>

                <p className="mt-3 text-3xl font-black text-[#FFB703]">

                    ₹{product.price}

                </p>

                <p className="mt-2 text-green-400">

                    {product.stock} in stock

                </p>

            </div>

        </Link>

    );

}