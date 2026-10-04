/** Public food library routes — Vietnamese paths only. */
export const FOOD_HUB_HREF = "/thuc-an";
export const FOODS_HREF = "/thuc-an";
export const DISHES_HREF = "/mon-truyen-thong";
export const COOK_HREF = "/cach-nau";

/** Subtitle under food hub titles (cách nấu, món truyền thống, kho thực phẩm). */
export const FOOD_AI_REFERENCE_NOTE =
  "Ảnh, công thức và mẹo nấu từ kho thực phẩm TAPTOT do AI tạo/tổng hợp, chỉ mang tính tham khảo — không thay tư vấn dinh dưỡng hay y tế.";

/** Detail URL for a cooking post (query form — avoids broken Next dynamic `/cach-nau/[slug]` in dev). */
export function foodHref(slug: string): string {
  const s = (slug || "").trim();
  if (!s) return FOODS_HREF;
  return `${FOODS_HREF}?slug=${encodeURIComponent(s)}`;
}

export function cookPostHref(slug: string): string {
  const s = (slug || "").trim();
  if (!s) return COOK_HREF;
  return `${COOK_HREF}?mon=${encodeURIComponent(s)}`;
}
