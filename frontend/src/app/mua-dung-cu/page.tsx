import ShopCatalog from "@/components/ShopCatalog";
import ShopProductDetail from "@/components/ShopProductDetail";
import { fetchSitePageMedia } from "@/lib/sitePageMedia";

export const metadata = {
  title: "Mua dụng cụ — TAPTOT",
  description: "Chọn dụng cụ TAPTOT, nhận mã trên tem và tạo lộ trình tập, ăn 100 ngày theo thể trạng của bạn.",
};

type ShopPageProps = {
  searchParams: Promise<{
    product?: string | string[];
    group?: string | string[];
    category?: string | string[];
    "san-pham"?: string | string[];
    "uu-dai"?: string | string[];
  }>;
};

function first(value?: string | string[]): string {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const productSlug = first(params["san-pham"]);
  if (productSlug) {
    return <ShopProductDetail slug={productSlug} />;
  }
  const media = await fetchSitePageMedia();
  return (
    <ShopCatalog
      initialProduct={first(params.product)}
      initialGroup={first(params.group)}
      initialCategory={first(params.category)}
      media={media}
      scrollToOffer={first(params["uu-dai"]) === "1"}
    />
  );
}
