import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { getRegistrationStatus } from "../services/supplierService";

export default function AccountStatus() {
  const navigate = useNavigate();
  const [state, setState] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getRegistrationStatus()
      .then((data) => {
        setState(data);
        if (data?.account_status === "ACTIVE") navigate("/", { replace: true });
      })
      .catch((err) =>
        setError(
          err?.response?.data?.message || "Unable to load account status.",
        ),
      );
  }, [navigate]);

  if (!state && !error)
    return (
      <div className="status-screen">
        <div className="status-card">Loading account status…</div>
      </div>
    );

  const status = String(state?.account_status || "UNKNOWN").toUpperCase();
  const feePaid = Boolean(state?.registration_fee_paid);
  const title =
    status === "PENDING" && !feePaid
      ? "Complete supplier onboarding"
      : "Supplier account access is restricted";
  const description =
    status === "PENDING" && !feePaid
      ? "Your supplier account is created, but the registration payment has not been verified yet."
      : `Current account state: ${status}. Access is controlled by Clipcart account workflow.`;

  return (
    <div className="status-screen">
      <div className="status-card">
        <div className="brand-mark">
          CLIPCART <span>SUPPLIER</span>
        </div>
        <div className={`status-pill status-${status.toLowerCase()}`}>
          {status}
        </div>
        <h1>{title}</h1>
        <p>{error || description}</p>
        <div className="status-steps">
          <div>
            <span className={feePaid ? "done" : ""}>1</span>
            <div>
              <strong>Account created</strong>
              <small>Supplier credentials are registered.</small>
            </div>
          </div>
          <div>
            <span className={feePaid ? "done" : ""}>2</span>
            <div>
              <strong>Registration fee verified</strong>
              <small>
                {feePaid
                  ? "Payment verified server-side."
                  : "Required before portal access."}
              </small>
            </div>
          </div>
          <div>
            <span
              className={
                state?.business_verification_status === "APPROVED" ? "done" : ""
              }
            >
              3
            </span>
            <div>
              <strong>Business verification</strong>
              <small>{state?.business_verification_status || "PENDING"}</small>
            </div>
          </div>
        </div>
        <div className="status-actions">
          {status === "PENDING" && !feePaid && (
            <Link className="primary-btn" to="/register/payment">
              Complete payment
            </Link>
          )}
          <Link className="secondary-btn" to="/login">
            Back to login
          </Link>
        </div>
      </div>
    </div>
  );
}
