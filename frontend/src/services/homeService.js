import { getHomeData } from "./storeService";

export { getHomeData };

export async function getTrendingProducts() {
  const data = await getHomeData();
  return data?.trending || [];
}
