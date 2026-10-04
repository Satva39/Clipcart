import { discountPercent, formatCurrency } from "../../utils/formatters";

export default function Price({ price, comparePrice, size = "md" }) {
  const discount = discountPercent(price, comparePrice);
  return (
    <div className={`cc-price-block ${size}`}>
      <span className="cc-price">{formatCurrency(price)}</span>
      {comparePrice && Number(comparePrice) > Number(price) ? (
        <>
          <span className="cc-mrp">{formatCurrency(comparePrice)}</span>
          <span className="cc-discount">{discount}% off</span>
        </>
      ) : null}
    </div>
  );
}
