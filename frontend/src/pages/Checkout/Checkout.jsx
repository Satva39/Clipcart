import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { FiCheck, FiEdit2, FiMapPin, FiShield, FiTrash2 } from "react-icons/fi";
import { useAuth } from "../../context/AuthContext";
import { useCart } from "../../context/CartContext";
import { applyCoupon } from "../../services/couponService";
import {
  createAddress,
  deleteAddress,
  getAddresses,
  updateAddress,
} from "../../services/addressService";
import {
  createCheckoutSession,
  createRazorpayOrder,
  getCheckoutSession,
  paymentFailed,
  selectCheckoutAddress,
  verifyPayment,
} from "../../services/orderService";
import loadRazorpay from "../../utils/loadRazorpay";
import { getApiMessage } from "../../utils/apiError";
import { formatCurrency } from "../../utils/formatters";
import Container from "../../components/common/Container";

const emptyForm = {
  full_name: "",
  phone: "",
  address_line_1: "",
  address_line_2: "",
  landmark: "",
  city: "",
  state: "",
  postal_code: "",
  country: "India",
  latitude: null,
  longitude: null,
  is_default: false,
};

export default function Checkout() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { cartItems, clearCart } = useCart();
  const [addresses, setAddresses] = useState([]);
  const [selectedAddressId, setSelectedAddressId] = useState(null);
  const [editingAddressId, setEditingAddressId] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [coupon, setCoupon] = useState("");
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [couponMessage, setCouponMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [couponBusy, setCouponBusy] = useState(false);
  const [addressBusy, setAddressBusy] = useState(false);

  const totalItems = useMemo(
    () => cartItems.reduce((sum, item) => sum + Number(item.quantity || 0), 0),
    [cartItems],
  );

  async function refreshCheckout() {
    const data = await getCheckoutSession();
    setSummary(data);
    if (data?.coupon?.code) setCoupon(data.coupon.code);
    return data;
  }

  useEffect(() => {
    if (!user) return;
    let active = true;

    async function initializeCheckout() {
      try {
        const [addressData, session] = await Promise.all([
          getAddresses(),
          createCheckoutSession(),
        ]);
        if (!active) return;

        const list = Array.isArray(addressData) ? addressData : [];
        setAddresses(list);

        const preferred =
          list.find((item) => item.id === session?.address_id) ||
          list.find((item) => item.is_default) ||
          list[0];

        setSelectedAddressId(preferred?.id || null);
        if (preferred) setForm((current) => ({ ...current, ...preferred }));
        if (session?.coupon?.code) setCoupon(session.coupon.code);

        let nextSession = session;

        // The backend decides whether payment is allowed. A preferred address
        // shown as selected in the UI must also be persisted on the checkout
        // session, otherwise `can_pay` remains false and the Pay button is
        // disabled even though an address card has a checkmark.
        if (preferred && !session?.address_id) {
          try {
            nextSession = await selectCheckoutAddress(preferred.id);
          } catch (err) {
            if (active) {
              setError(
                getApiMessage(
                  err,
                  "Couldn't select the delivery address. Please choose the address again.",
                ),
              );
            }
          }
        }

        if (!active) return;
        setSummary(nextSession);
      } catch (err) {
        if (active) setError(getApiMessage(err, "Couldn't load checkout."));
      }
    }

    initializeCheckout();

    return () => {
      active = false;
    };
  }, [user]);

  if (!user) return null;

  if (!cartItems.length) {
    return (
      <div className="cc-page-shell">
        <Container>
          <div className="cc-state-panel">
            <h3>Your cart is empty</h3>
            <p>Add something before starting checkout.</p>
            <Link className="cc-btn primary" to="/products">
              Continue shopping
            </Link>
          </div>
        </Container>
      </div>
    );
  }

  function startAdd() {
    setEditingAddressId(null);
    setForm({
      ...emptyForm,
      full_name: user.full_name || "",
      phone: user.phone || "",
    });
    setShowForm(true);
  }

  function startEdit(address) {
    setEditingAddressId(address.id);
    setForm({ ...emptyForm, ...address });
    setShowForm(true);
  }

  function captureDeliveryLocation() {
    if (!navigator.geolocation) {
      setError("This browser does not support location access.");
      return;
    }
    setError("");
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setForm((current) => ({
          ...current,
          latitude: Number(position.coords.latitude.toFixed(7)),
          longitude: Number(position.coords.longitude.toFixed(7)),
        }));
      },
      () =>
        setError(
          "Location permission was unavailable. You can still enter the address manually.",
        ),
      { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
    );
  }

  async function saveAddress(event) {
    event.preventDefault();
    setAddressBusy(true);
    setError("");
    try {
      const saved = editingAddressId
        ? await updateAddress(editingAddressId, form)
        : await createAddress(form);
      setAddresses((current) => {
        const mapped = current.filter((item) => item.id !== saved.id);
        return [saved, ...mapped].map((item) => ({
          ...item,
          is_default: form.is_default ? item.id === saved.id : item.is_default,
        }));
      });
      setSelectedAddressId(saved.id);
      await selectCheckoutAddress(saved.id);
      await refreshCheckout();
      setEditingAddressId(null);
      setShowForm(false);
    } catch (err) {
      setError(getApiMessage(err, "Couldn't save the delivery address."));
    } finally {
      setAddressBusy(false);
    }
  }

  async function deleteSavedAddress(addressId) {
    try {
      await deleteAddress(addressId);
      const next = addresses.filter((item) => item.id !== addressId);
      setAddresses(next);
      if (selectedAddressId === addressId) {
        const nextId = next[0]?.id || null;
        setSelectedAddressId(nextId);
        if (nextId) await selectCheckoutAddress(nextId);
      }
      await refreshCheckout();
    } catch (err) {
      setError(getApiMessage(err, "Couldn't delete the address."));
    }
  }

  async function chooseAddress(address) {
    setSelectedAddressId(address.id);
    setForm((current) => ({ ...current, ...address }));
    setError("");
    try {
      const data = await selectCheckoutAddress(address.id);
      setSummary(data);
    } catch (err) {
      setError(getApiMessage(err, "Couldn't select this address."));
    }
  }

  async function couponApply() {
    setCouponBusy(true);
    setCouponMessage("");
    try {
      const data = await applyCoupon(coupon.trim());
      setSummary(data.data || data);
      setCouponMessage(coupon.trim() ? "Coupon applied." : "Coupon removed.");
    } catch (err) {
      setCouponMessage(getApiMessage(err, "That coupon could not be applied."));
      try {
        await refreshCheckout();
      } catch {
        /* preserve original message */
      }
    } finally {
      setCouponBusy(false);
    }
  }

  async function placeOrder() {
    setBusy(true);
    setError("");
    try {
      const latest = await refreshCheckout();
      if (!latest?.address_id)
        throw new Error("Please select a delivery address.");
      if (latest.issues?.length)
        throw new Error(
          "Please resolve unavailable or out-of-stock items before payment.",
        );
      if (!latest.can_pay)
        throw new Error("Checkout is not ready for payment.");

      const loaded = await loadRazorpay();
      if (!loaded || !window.Razorpay)
        throw new Error("Payment service could not be loaded.");

      const paymentOrder = await createRazorpayOrder();
      const publicKey = paymentOrder.public_key || latest.razorpay_key_id;
      if (!publicKey) throw new Error("Razorpay public key is not configured.");

      const razorpay = new window.Razorpay({
        key: publicKey,
        amount: paymentOrder.amount,
        currency: paymentOrder.currency || "INR",
        name: "Clipcart",
        description: `Clipcart order · ${totalItems} item${totalItems !== 1 ? "s" : ""}`,
        order_id: paymentOrder.razorpay_order_id,
        prefill: {
          name: form.full_name || user.full_name,
          email: user.email,
          contact: form.phone || user.phone,
        },
        theme: { color: "#f7b500" },
        modal: {
          ondismiss: () => setBusy(false),
          escape: false,
        },
        handler: async (response) => {
          try {
            // Payment verification is the authoritative success boundary.
            // The backend finalizes the order (and clears the persisted cart)
            // before returning a successful verification response.
            const result = await verifyPayment(response);
            const orderId = Number(result?.order_id);

            if (!Number.isInteger(orderId) || orderId <= 0) {
              throw new Error(
                "Order was created but no order ID was returned.",
              );
            }

            // Cart cleanup is best-effort after a successful payment/order.
            // It must never turn a completed order into a payment error.
            try {
              await clearCart();
            } catch {
              // The backend has already finalized the order and removed its
              // cart items. Navigation must still continue.
            }

            navigate("/orders", {
              replace: true,
            });
          } catch (err) {
            setError(
              getApiMessage(
                err,
                "Payment was received but order confirmation could not be completed.",
              ),
            );
            setBusy(false);
          }
        },
      });
      razorpay.on("payment.failed", async (response) => {
        try {
          const result = await paymentFailed(response);
          setError(result?.message || "Payment was not completed.");
        } catch (err) {
          setError(getApiMessage(err, "Payment failed. You can try again."));
        } finally {
          setBusy(false);
        }
      });
      razorpay.open();
    } catch (err) {
      setError(getApiMessage(err, "Unable to start checkout."));
      setBusy(false);
    }
  }

  const checkoutItems =
    summary?.items ||
    cartItems.map((item) => ({
      name: item.name,
      variant_value: item.variant_value,
      quantity: item.quantity,
      unit_price: item.price,
      item_subtotal: item.item_total,
      available: item.stock >= item.quantity,
      available_stock: item.stock,
    }));

  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-page-heading">
          <div>
            <span className="cc-eyebrow">Secure checkout</span>
            <h1>Checkout</h1>
            <p>
              The backend recalculates and locks the payable amount before
              Razorpay opens.
            </p>
          </div>
          <span className="cc-secure-note">
            <FiShield /> Protected payment
          </span>
        </div>

        {error ? (
          <div className="cc-form-error" role="alert">
            {error}
          </div>
        ) : null}

        {summary?.issues?.length ? (
          <div className="cc-form-error" role="alert">
            <strong>Some cart items need attention:</strong>
            <div>
              {summary.issues.map((issue) => (
                <div key={`${issue.cart_item_id}-${issue.message}`}>
                  {issue.message}
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {summary?.shipping_error ? (
          <div className="cc-form-error" role="alert">
            Delivery charge unavailable: {summary.shipping_error}
          </div>
        ) : null}

        <div className="cc-checkout-layout">
          <section className="cc-checkout-main">
            <div className="cc-checkout-card">
              <div className="cc-card-head">
                <div>
                  <h2>Delivery address</h2>
                  <p>Select, edit or add the address for this order.</p>
                </div>
                <button
                  type="button"
                  className="cc-btn secondary"
                  onClick={startAdd}
                >
                  <FiMapPin /> Add new
                </button>
              </div>

              {addresses.length ? (
                <div className="cc-address-grid checkout">
                  {addresses.map((address) => (
                    <article
                      key={address.id}
                      className={`cc-address-card ${selectedAddressId === address.id ? "selected" : ""}`}
                    >
                      <button
                        type="button"
                        className="cc-address-select"
                        onClick={() => chooseAddress(address)}
                      >
                        <div>
                          <strong>{address.full_name}</strong>
                          <p>
                            {address.address_line_1}
                            {address.address_line_2
                              ? `, ${address.address_line_2}`
                              : ""}
                          </p>
                          <p>
                            {address.city}, {address.state}{" "}
                            {address.postal_code}
                          </p>
                          <small>{address.phone}</small>
                        </div>
                        <span>
                          {selectedAddressId === address.id ? (
                            <FiCheck />
                          ) : null}
                        </span>
                      </button>
                      <div className="cc-inline-actions">
                        <button
                          type="button"
                          className="cc-link-button"
                          onClick={() => startEdit(address)}
                        >
                          <FiEdit2 /> Edit
                        </button>
                        <button
                          type="button"
                          className="cc-link-button danger"
                          onClick={() => deleteSavedAddress(address.id)}
                        >
                          <FiTrash2 /> Delete
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <div className="cc-slim-empty">
                  No saved addresses yet. Add one to continue.
                </div>
              )}

              {showForm ? (
                <form
                  className="cc-form compact checkout-form"
                  onSubmit={saveAddress}
                >
                  <div className="cc-inline-actions">
                    <button
                      type="button"
                      className="cc-btn secondary"
                      onClick={captureDeliveryLocation}
                    >
                      <FiMapPin /> Use current delivery location
                    </button>
                    {form.latitude != null && form.longitude != null ? (
                      <small>Location captured for shipment mapping.</small>
                    ) : null}
                  </div>
                  <div className="cc-two-col">
                    {[
                      ["full_name", "Full name", true],
                      ["phone", "Phone", true],
                      ["address_line_1", "Address line 1", true],
                      ["address_line_2", "Address line 2", false],
                      ["landmark", "Landmark", false],
                      ["city", "City", true],
                      ["state", "State", true],
                      ["postal_code", "Postal code", true],
                    ].map(([field, label, required]) => (
                      <label
                        key={field}
                        className={field === "address_line_1" ? "wide" : ""}
                      >
                        {label}
                        <input
                          required={required}
                          value={form[field]}
                          onChange={(e) =>
                            setForm((current) => ({
                              ...current,
                              [field]: e.target.value,
                            }))
                          }
                          inputMode={
                            field === "phone" || field === "postal_code"
                              ? "numeric"
                              : undefined
                          }
                        />
                      </label>
                    ))}
                  </div>
                  <label className="cc-check">
                    <input
                      type="checkbox"
                      checked={Boolean(form.is_default)}
                      onChange={(e) =>
                        setForm((current) => ({
                          ...current,
                          is_default: e.target.checked,
                        }))
                      }
                    />{" "}
                    Make default
                  </label>
                  <div className="cc-inline-actions">
                    <button
                      type="submit"
                      className="cc-btn primary"
                      disabled={addressBusy}
                    >
                      {addressBusy
                        ? "Saving…"
                        : editingAddressId
                          ? "Save changes"
                          : "Save address"}
                    </button>
                    <button
                      type="button"
                      className="cc-btn secondary"
                      onClick={() => setShowForm(false)}
                    >
                      Close
                    </button>
                  </div>
                </form>
              ) : null}
            </div>

            <div className="cc-checkout-card">
              <div className="cc-card-head">
                <div>
                  <h2>Items</h2>
                  <p>
                    {summary?.total_items ?? totalItems} item
                    {(summary?.total_items ?? totalItems) !== 1 ? "s" : ""} in
                    your cart.
                  </p>
                </div>
              </div>
              <div className="cc-checkout-items">
                {checkoutItems.map((item, index) => (
                  <div
                    key={`${item.cart_item_id || item.product_id || index}-${item.variant_id || "base"}`}
                  >
                    <span>
                      {item.name}
                      {item.variant_value
                        ? ` · ${item.variant_value}`
                        : ""} × {item.quantity}
                      {!item.available
                        ? ` · ${item.available_stock ?? 0} available`
                        : ""}
                    </span>
                    <strong>
                      {formatCurrency(
                        item.item_subtotal ?? item.unit_price * item.quantity,
                      )}
                    </strong>
                  </div>
                ))}
              </div>
            </div>
          </section>

          <aside className="cc-summary-card checkout">
            <h2>Order total</h2>
            <div className="cc-summary-lines">
              <span>
                Subtotal{" "}
                <strong>{formatCurrency(summary?.subtotal ?? 0)}</strong>
              </span>
              <span>
                Discount{" "}
                <strong>− {formatCurrency(summary?.discount ?? 0)}</strong>
              </span>
              <span>
                Marketing fee{" "}
                <strong>{formatCurrency(summary?.marketing_fee ?? 0)}</strong>
              </span>
              <span>
                Tax <strong>{formatCurrency(summary?.tax ?? 0)}</strong>
              </span>
              <span>
                Delivery charge
                <strong>{formatCurrency(summary?.shipping_charge ?? 0)}</strong>
              </span>
              <span className="total">
                Payable <strong>{formatCurrency(summary?.total ?? 0)}</strong>
              </span>
            </div>

            <div className="cc-coupon">
              <div>
                <input
                  value={coupon}
                  onChange={(e) => setCoupon(e.target.value.toUpperCase())}
                  placeholder="Coupon code"
                />
                <button
                  type="button"
                  onClick={couponApply}
                  disabled={couponBusy}
                >
                  {couponBusy ? "…" : "Apply"}
                </button>
              </div>
              {couponMessage ? <small>{couponMessage}</small> : null}
            </div>

            {summary?.estimated_delivery ? (
              <div className="cc-slim-empty">
                <strong>{summary.estimated_delivery.label}</strong>
                {summary.estimated_delivery.window ? (
                  <>
                    <br />
                    {summary.estimated_delivery.window}
                  </>
                ) : (
                  <>
                    <br />
                    Available after supplier processing
                  </>
                )}
              </div>
            ) : null}

            <button
              type="button"
              className="cc-btn primary full"
              disabled={busy || !summary?.can_pay}
              onClick={placeOrder}
            >
              {busy
                ? "Processing payment…"
                : `Pay ${formatCurrency(summary?.total ?? 0)}`}
            </button>
            <p className="cc-summary-note">
              The amount shown here comes from the backend. Razorpay receives
              that same server-calculated amount.
            </p>
          </aside>
        </div>
      </Container>
    </div>
  );
}
