import { useEffect, useState } from "react";
import { getProducts } from "../services/productService";

export default function useProducts() {

    const [products, setProducts] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {

        async function load() {

            try {

                const data = await getProducts();

                setProducts(Array.isArray(data) ? data : []);

            } catch (err) {

                console.error(err);

                setProducts([]);

            } finally {

                setLoading(false);

            }

        }

        load();

    }, []);

    return {
        products,
        loading,
    };

}