import { FiCheckCircle, FiPackage } from "react-icons/fi";
import { Link, useSearchParams } from "react-router-dom";
import Container from "../../components/common/Container";

export default function OrderSuccess() {
  const [params] = useSearchParams();
  const orderId = params.get("order");
  return (
    <div className="cc-page-shell">
      <Container>
        <div className="cc-success-card">
          <FiCheckCircle />
          <span className="cc-eyebrow">Order confirmed</span>
          <h1>Thanks for shopping with Clipcart.</h1>
          <p>
            Your payment and order creation flow completed.{" "}
            {orderId
              ? `Order #${orderId} is now available in your account.`
              : "You can find your latest order in your order history."}
          </p>
          <div className="cc-inline-actions center">
            <Link className="cc-btn primary" to="/orders">
              <FiPackage /> View orders
            </Link>
            <Link className="cc-btn secondary" to="/products">
              Continue shopping
            </Link>
          </div>
        </div>
      </Container>
    </div>
  );
}
