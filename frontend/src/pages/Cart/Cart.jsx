import { Link } from "react-router-dom";
import { FiMinus, FiPlus, FiTrash2 } from "react-icons/fi";
import { useCart } from "../../context/CartContext";

export default function Cart() {
  const { cartItems, cartSubtotal, updateQuantity, removeFromCart } = useCart();

  if (cartItems.length === 0) {
    return (
      <section className="min-h-[70vh] px-6 py-20">
        <div className="mx-auto max-w-3xl rounded-2xl bg-[#232F3E] p-16 text-center">
          <h1 className="text-4xl font-black">Your Cart is Empty</h1>

          <p className="mt-4 text-gray-400">
            Looks like you haven't added anything to your cart yet.
          </p>

          <Link
            to="/"
            className="mt-8 inline-block rounded-xl bg-[#FFB703] px-8 py-4 font-bold text-black"
          >
            Continue Shopping
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-[1600px] px-6 py-12">
      <h1 className="mb-10 text-5xl font-black">Shopping Cart</h1>

      <div className="grid gap-8 lg:grid-cols-[1fr_420px]">
        {/* Cart Items */}
        <div className="space-y-6">
          {cartItems.map((item) => (
            <div key={item.id} className="rounded-2xl bg-[#232F3E] p-6">
              <div className="flex flex-col gap-6 md:flex-row">
                {/* Product Image */}
                <div className="flex h-44 w-full shrink-0 items-center justify-center rounded-xl bg-[#131921] md:w-44">
                  <span className="text-2xl font-black">Clipcart</span>
                </div>

                {/* Product Details */}
                <div className="flex flex-1 flex-col justify-between">
                  <div>
                    <p className="text-sm uppercase text-[#FFB703]">
                      {item.category || "Product"}
                    </p>

                    <h2 className="mt-2 text-2xl font-bold">{item.name}</h2>

                    <p className="mt-2 text-gray-400">
                      Seller: {item.supplier_name || "Clipcart Official"}
                    </p>
                  </div>

                  <div className="mt-6 flex flex-wrap items-center justify-between gap-5">
                    {/* Price */}
                    <div>
                      <p className="text-3xl font-black text-[#FFB703]">
                        ₹{Number(item.price).toFixed(0)}
                      </p>

                      {item.compare_price &&
                        Number(item.compare_price) > Number(item.price) && (
                          <p className="text-sm text-gray-500 line-through">
                            ₹{Number(item.compare_price).toFixed(0)}
                          </p>
                        )}
                    </div>

                    {/* Quantity */}
                    <div className="flex items-center overflow-hidden rounded-lg border border-gray-600">
                      <button
                        onClick={() =>
                          updateQuantity(item.id, item.quantity - 1)
                        }
                        className="px-4 py-3 transition hover:bg-[#131921]"
                        aria-label="Decrease quantity"
                      >
                        <FiMinus />
                      </button>

                      <span className="min-w-12 px-4 text-center font-bold">
                        {item.quantity}
                      </span>

                      <button
                        onClick={() =>
                          updateQuantity(item.id, item.quantity + 1)
                        }
                        className="px-4 py-3 transition hover:bg-[#131921]"
                        aria-label="Increase quantity"
                      >
                        <FiPlus />
                      </button>
                    </div>

                    {/* Item Total */}
                    <div className="text-right">
                      <p className="text-sm text-gray-400">Item Total</p>

                      <p className="text-xl font-bold">
                        ₹{(Number(item.price) * item.quantity).toFixed(0)}
                      </p>
                    </div>
                  </div>

                  {/* Remove */}
                  <button
                    onClick={() => removeFromCart(item.id)}
                    className="mt-5 flex w-fit items-center gap-2 text-red-400 transition hover:text-red-300"
                  >
                    <FiTrash2 />
                    Remove
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <aside className="h-fit rounded-2xl bg-[#232F3E] p-8 lg:sticky lg:top-24">
          <h2 className="text-3xl font-black">Order Summary</h2>

          <div className="mt-8 space-y-5">
            <div className="flex justify-between">
              <span>Subtotal</span>
              <span>₹{cartSubtotal.toFixed(0)}</span>
            </div>

            <div className="flex justify-between">
              <span>Shipping</span>
              <span>Calculated at checkout</span>
            </div>

            <div className="flex justify-between">
              <span>Tax</span>
              <span>₹0</span>
            </div>
          </div>

          <div className="my-6 border-t border-gray-700" />

          <div className="flex justify-between text-2xl font-black">
            <span>Total</span>

            <span className="text-[#FFB703]">₹{cartSubtotal.toFixed(0)}</span>
          </div>

          <Link
            to="/checkout"
            className="mt-8 block w-full rounded-xl bg-[#FFB703] py-4 text-center text-lg font-bold text-black transition hover:scale-[1.02]"
          >
            Proceed to Checkout
          </Link>
        </aside>
      </div>
    </section>
  );
}
