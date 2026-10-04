import { useQuery } from "@tanstack/react-query";
import { getHomeData } from "../../services/homeService";
import { getRecommendations } from "../../services/storeService";
import { getRecentlyViewedIds } from "../../utils/recentlyViewed";
import Container from "../../components/common/Container";
import { ErrorState } from "../../components/common/AsyncState";
import CategoryDiscovery from "../../components/home/CategoryDiscovery";
import Brands from "../../components/home/Brands";
import HeroSlider from "../../components/home/HeroSlider";
import HomeBannerStrip from "../../components/home/HomeBannerStrip";
import FlashDeals from "../../components/home/FlashDeals";
import TrendingSection from "../../components/home/TrendingSection";
import FeaturedProducts from "../../components/home/FeaturedProducts";
import ProductShelf from "../../components/home/ProductShelf";
import RecentlyViewed from "../../components/sections/RecentlyViewed";

export default function Home() {
  const homeQuery = useQuery({
    queryKey: ["store", "home"],
    queryFn: getHomeData,
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
  });

  const viewedIds = getRecentlyViewedIds();
  const recommendationQuery = useQuery({
    queryKey: ["store", "recommendations", viewedIds.join(",")],
    queryFn: () => getRecommendations({ viewedIds }),
    enabled: viewedIds.length > 0,
  });

  if (homeQuery.isError) {
    return (
      <div className="cc-page-shell">
        <Container>
          <ErrorState
            message="We couldn't load the Clipcart storefront."
            onRetry={() => homeQuery.refetch()}
          />
        </Container>
      </div>
    );
  }

  const data = homeQuery.data || {};
  const banners = Array.isArray(data.banners) ? data.banners : [];
  const loading = homeQuery.isLoading;
  const announcement = data.public_settings?.customer_announcement;
  const recommendations = recommendationQuery.data || [];

  return (
    <>
      {announcement ? (
        <div className="cc-platform-announcement" role="status">
          {announcement}
        </div>
      ) : null}
      <HeroSlider slides={data.hero || []} banners={banners} />
      <HomeBannerStrip
        banners={banners}
        placement="HOME_PROMO"
        label="Clipcart promotions"
      />
      <FlashDeals count={(data.deals || []).length} />
      <CategoryDiscovery categories={data.categories || []} />
      <HomeBannerStrip
        banners={banners}
        placement="HOME_CATEGORY"
        label="Clipcart category promotions"
      />
      <TrendingSection products={data.trending || []} loading={loading} />
      <FeaturedProducts products={data.featured || []} loading={loading} />
      {recommendationQuery.isError ? null : (
        <ProductShelf
          title="Recommended for you"
          description={
            recommendations.length
              ? "Based on products you have viewed."
              : "Recommendations appear after you browse products."
          }
          products={recommendations}
          loading={recommendationQuery.isLoading && viewedIds.length > 0}
        />
      )}
      <ProductShelf
        title="Best sellers"
        description="Popular products across the marketplace."
        products={data.best_sellers || []}
        loading={loading}
        to="/products?sort=popular"
      />
      <ProductShelf
        title="New arrivals"
        description="The latest active products added to Clipcart."
        products={data.new_arrivals || []}
        loading={loading}
        to="/products?sort=newest"
      />
      <ProductShelf
        title="Deals worth a look"
        description="Products where the seller has supplied a compare price above the current price."
        products={data.deals || []}
        loading={loading}
        to="/products?discount=true&sort=discount"
      />
      <RecentlyViewed />
      <Brands brands={data.brands || []} />
    </>
  );
}
