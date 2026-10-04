import { Link } from "react-router-dom";

function BannerContent({ banner, className }) {
  const image = banner?.image_url;
  const title = banner?.title || "Clipcart promotion";
  if (!image) return null;
  const content = <img src={image} alt={title} loading="lazy" />;
  const destination = String(banner?.destination || "").trim();
  if (!destination) return <div className={className}>{content}</div>;
  if (/^https?:\/\//i.test(destination)) {
    return (
      <a
        className={className}
        href={destination}
        target="_blank"
        rel="noreferrer"
      >
        {content}
      </a>
    );
  }
  return (
    <Link
      className={className}
      to={destination.startsWith("/") ? destination : `/${destination}`}
    >
      {content}
    </Link>
  );
}

export default function HomeBannerStrip({ banners = [], placement, label }) {
  const rows = banners.filter(
    (banner) => banner?.placement === placement && banner?.image_url,
  );
  if (!rows.length) return null;
  return (
    <section
      className="cc-banner-strip"
      aria-label={label || "Clipcart promotional banners"}
    >
      <div className="cc-container cc-banner-strip-grid">
        {rows.slice(0, 4).map((banner) => (
          <BannerContent
            key={banner.id}
            banner={banner}
            className="cc-banner-strip-card"
          />
        ))}
      </div>
    </section>
  );
}
