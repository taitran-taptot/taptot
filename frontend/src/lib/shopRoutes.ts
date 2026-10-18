/** Public shop product URLs (Vietnamese). Legacy English kit slugs still resolve. */

export const SHOP_PATH_BY_KIT: Record<string, string> = {
  "resistance-band": "day-khang-luc",
  dumbbell: "ta-don",
  "bar-and-rings": "xa-don-va-vong-treo",
};

export const SHOP_KIT_BY_PATH: Record<string, string> = {
  "day-khang-luc": "resistance-band",
  "ta-don": "dumbbell",
  "xa-don-va-vong-treo": "bar-and-rings",
};

export function canonicalShopPathSlug(slug: string): string {
  const key = (slug || "").trim();
  if (!key) return key;
  if (SHOP_PATH_BY_KIT[key]) return SHOP_PATH_BY_KIT[key];
  if (SHOP_KIT_BY_PATH[key]) return key;
  return key;
}

export function shopProductHref(slug: string): string {
  return `/mua-dung-cu/${canonicalShopPathSlug(slug)}`;
}

export function isShopDumbbellSlug(slug: string): boolean {
  return slug === "dumbbell" || slug === "ta-don";
}

export function isShopBarKitSlug(slug: string): boolean {
  return slug === "bar-and-rings" || slug === "xa-don-va-vong-treo";
}
