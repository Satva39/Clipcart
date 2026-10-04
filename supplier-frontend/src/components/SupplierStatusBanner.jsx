export default function SupplierStatusBanner({ profile }) {
  const accountStatus = profile?.account?.status;
  const verification = profile?.business?.verification_status;
  if (!profile || accountStatus !== "ACTIVE") return null;
  if (verification && verification !== "APPROVED") {
    return (
      <div className="supplier-status-banner info">
        <strong>Business verification: {verification}</strong>
        <span>
          Your storefront operations are active, but your business verification
          is still being reviewed.
        </span>
      </div>
    );
  }
  return null;
}
