import { useState } from "react";

export default function BrandLogo({ className = "" }) {
  const [failed, setFailed] = useState(false);

  return (
    <span className={`cc-logo ${className}`.trim()}>
      {!failed ? (
        <img
          src="/clipcart-logo.png"
          alt="Clipcart"
          onError={() => setFailed(true)}
        />
      ) : null}
      <span className={`cc-logo-fallback ${failed ? "visible" : ""}`}>
        Clip<span>cart</span>
      </span>
    </span>
  );
}
