import ShopCatalog from "@/components/ShopCatalog";

export const metadata = {
  title: "Mua dụng cụ — TAPTOT",
  description: "Chọn dụng cụ TAPTOT, nhận mã trên tem và tạo lộ trình tập, ăn 100 ngày theo thể trạng của bạn.",
};

type ShopPageProps = {
  searchParams: Promise<{
    product?: string | string[];
    group?: string | string[];
    category?: string | string[];
    from?: string | string[];
  }>;
};

function first(value?: string | string[]): string {
  return Array.isArray(value) ? value[0] || "" : value || "";
}

export default async function ShopPage({ searchParams }: ShopPageProps) {
  const params = await searchParams;
  const source = first(params.from);
  return (
    <ShopCatalog
      initialProduct={first(params.product)}
      initialGroup={first(params.group)}
      initialCategory={first(params.category)}
      highlightGiftOffer={source === "hero" || source === "challenge"}
    />
  );
}
