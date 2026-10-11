import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createRegistrationPayment,
  getRegistrationStatus,
  verifyRegistrationPayment,
} from "../../services/supplierService";
import "./auth.css";

export default function RegisterPayment() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState("");
  const [state, setState] = useState(null);
  useEffect(() => {
    getRegistrationStatus()
      .then((s) => {
        setState(s);
        if (s.account_status === "ACTIVE") navigate("/", { replace: true });
      })
      .catch((e) =>
        setError(e?.response?.data?.message || "Please sign in again."),
      )
      .finally(() => setLoading(false));
  }, [navigate]);
  const registrationFee = Number(state?.registration_fee);
  const feeIsValid = Number.isFinite(registrationFee) && registrationFee > 0;

  async function pay() {
    if (!state || !feeIsValid || state.registration_fee_paid) {
      setError(
        "A valid registration fee is not available yet. Refresh this page; if the issue continues, contact support.",
      );
      return;
    }
    setPaying(true);
    setError("");
    try {
      const order = await createRegistrationPayment();
      const amountPaise = Number(order.amount_paise);
      const amountFromRupees = Math.round(Number(order.amount) * 100);
      const verifiedAmountPaise =
        Number.isSafeInteger(amountPaise) && amountPaise > 0
          ? amountPaise
          : amountFromRupees;
      if (
        !Number.isSafeInteger(verifiedAmountPaise) ||
        verifiedAmountPaise <= 0
      ) {
        throw new Error(
          "The registration fee returned by the server is invalid. No payment was started.",
        );
      }
      if (!order.key_id || !order.order_id) {
        throw new Error(
          "Razorpay payment details are incomplete. Please contact support.",
        );
      }
      if (!window.Razorpay) {
        await new Promise((resolve, reject) => {
          const script = document.createElement("script");
          script.src = "https://checkout.razorpay.com/v1/checkout.js";
          script.onload = resolve;
          script.onerror = reject;
          document.body.appendChild(script);
        });
      }
      const razorpay = new window.Razorpay({
        key: order.key_id,
        amount: verifiedAmountPaise,
        currency: order.currency,
        name: "Clipcart",
        description: "Supplier Registration Fee",
        order_id: order.order_id,
        handler: async (response) => {
          try {
            const result = await verifyRegistrationPayment(response);
            if (result?.data?.status || result?.status === "ACTIVE") {
              const raw = localStorage.getItem("clipcart_supplier_user");
              let u = {};
              try {
                u = raw ? JSON.parse(raw) : {};
              } catch {
                /* ignore malformed local user */
              }
              localStorage.setItem(
                "clipcart_supplier_user",
                JSON.stringify({ ...u, status: "ACTIVE" }),
              );
              navigate("/", { replace: true });
            } else setError("Payment was not marked successful.");
          } catch (e) {
            setError(
              e?.response?.data?.message ||
                "Payment verification failed. Your account has not been activated.",
            );
          } finally {
            setPaying(false);
          }
        },
        modal: { ondismiss: () => setPaying(false) },
        theme: { color: "#111827" },
      });
      razorpay.open();
    } catch (e) {
      setError(
        e?.response?.data?.message ||
          e?.message ||
          "Unable to initialize the supplier registration payment.",
      );
      setPaying(false);
    }
  }
  if (loading)
    return (
      <div className="status-screen">
        <div className="status-card">Loading onboarding status…</div>
      </div>
    );
  return (
    <div className="auth-page-modern">
      <div className="payment-card-modern">
        <div className="auth-brand">
          CLIPCART <span>SUPPLIER</span>
        </div>
        <div className="auth-eyebrow">
          Step 2 of 2 · Verify registration fee
        </div>
        <h1>Activate your supplier account</h1>
        <p className="auth-subtitle">
          Your profile is created in a pending state. Portal access begins only
          after Razorpay payment verification succeeds on the server.
        </p>
        <div className="payment-amount">
          {feeIsValid ? (
            <>
              <span>₹</span>
              {registrationFee.toFixed(2)}
            </>
          ) : (
            <span className="payment-amount-unavailable">Fee unavailable</span>
          )}
        </div>
        <div className="payment-meta">
          <div>
            <span>Amount</span>
            <b>
              {feeIsValid ? `₹${registrationFee.toFixed(2)}` : "Unavailable"}
            </b>
          </div>
          <div>
            <span>Gateway</span>
            <b>Razorpay</b>
          </div>
          <div>
            <span>Status</span>
            <b>{state?.registration_fee_paid ? "Paid" : "Pending"}</b>
          </div>
        </div>
        {error && <div className="auth-error">{error}</div>}
        <button
          className="payment-main-btn"
          onClick={pay}
          disabled={
            loading ||
            paying ||
            !state ||
            !feeIsValid ||
            state?.registration_fee_paid
          }
        >
          {paying
            ? "Opening secure checkout…"
            : state?.registration_fee_paid
              ? "Payment already verified"
              : feeIsValid
                ? `Pay ₹${registrationFee.toFixed(2)} securely`
                : "Payment unavailable — reload details"}
        </button>
        <p className="auth-note">
          Do not close the page until Razorpay finishes. A successful browser
          callback alone does not activate the account; the backend verifies the
          Razorpay signature and captured payment first.
        </p>
        <Link className="back-link" to="/login">
          Return to login
        </Link>
      </div>
    </div>
  );
}
