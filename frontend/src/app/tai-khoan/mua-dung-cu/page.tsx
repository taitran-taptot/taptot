import ShopCatalog from "@/components/ShopCatalog";

type AccountShopPageProps = {
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

export default async function AccountShopPage({ searchParams }: AccountShopPageProps) {
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
