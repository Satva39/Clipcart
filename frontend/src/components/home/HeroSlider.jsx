import { useEffect, useState } from "react";
import { FiArrowRight, FiChevronLeft, FiChevronRight } from "react-icons/fi";
import { Link } from "react-router-dom";
import Container from "../common/Container";

function BannerLink({ destination, children, className }) {
  const href = String(destination || "").trim();

  if (!href) {
    return <div className={className}>{children}</div>;
  }

  if (/^https?:\/\//i.test(href)) {
    return (
      <a className={className} href={href} target="_blank" rel="noreferrer">
        {children}
      </a>
    );
  }

  return (
    <Link className={className} to={href.startsWith("/") ? href : `/${href}`}>
      {children}
    </Link>
  );
}

function StaticHero() {
  return (
    <section className="cc-static-hero" aria-label="Clipcart marketplace">
      <Container>
        <div className="cc-static-hero-copy">
          <span className="cc-eyebrow">Clipcart marketplace</span>
          <h1>Everything you need. One trusted place.</h1>
          <p>
            Discover products from independent sellers, compare prices, and shop
            with confidence on Clipcart.
          </p>
          <Link className="cc-btn primary" to="/products">
            Explore products <FiArrowRight />
          </Link>
        </div>
        <div className="cc-static-hero-art" aria-hidden="true">
          <div className="cc-static-hero-card large">
            <span>SHOP</span>
            <strong>Clipcart</strong>
          </div>
          <div className="cc-static-hero-card small top">
            <span>DEALS</span>
            <strong>Every day</strong>
          </div>
          <div className="cc-static-hero-card small bottom">
            <span>DELIVERY</span>
            <strong>Track with ease</strong>
          </div>
        </div>
      </Container>
    </section>
  );
}

export default function HeroSlider({ banners = [] }) {
  const heroBanners = (banners || []).filter(
    (banner) =>
      banner?.placement === "HOME_HERO" &&
      banner?.image_url &&
      banner?.visible !== false,
  );
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex((current) =>
      Math.min(current, Math.max(0, heroBanners.length - 1)),
    );
  }, [heroBanners.length]);

  useEffect(() => {
    if (heroBanners.length < 2) return undefined;

    const timer = window.setInterval(
      () => setIndex((current) => (current + 1) % heroBanners.length),
      5500,
    );

    return () => window.clearInterval(timer);
  }, [heroBanners.length]);

  if (!heroBanners.length) {
    return <StaticHero />;
  }

  const item = heroBanners[index];

  return (
    <section
      className="cc-hero cc-hero-banner"
      aria-roledescription="carousel"
      aria-label="Clipcart promotional banners"
    >
      <div className="cc-hero-banner-stage">
        <BannerLink
          destination={item.destination}
          className="cc-hero-banner-link"
        >
          <img
            src={item.image_url}
            alt={item.title || "Clipcart promotion"}
            loading="eager"
          />
        </BannerLink>

        {heroBanners.length > 1 ? (
          <div className="cc-hero-banner-controls" aria-label="Banner controls">
            <button
              type="button"
              className="cc-hero-banner-arrow"
              onClick={() =>
                setIndex(
                  (current) =>
                    (current - 1 + heroBanners.length) % heroBanners.length,
                )
              }
              aria-label="Previous banner"
            >
              <FiChevronLeft />
            </button>
            <button
              type="button"
              className="cc-hero-banner-arrow"
              onClick={() =>
                setIndex((current) => (current + 1) % heroBanners.length)
              }
              aria-label="Next banner"
            >
              <FiChevronRight />
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}
