import {
  WIZARD_EQUIPMENT_GROUPS,
  type WizardEquipmentGroupId,
} from "@/lib/equipmentCatalog";
import { EQUIPMENT_GROUP_UI, shopHrefForGroup } from "@/lib/equipmentGroupUi";

export const SHOP_CATEGORIES = [
  { key: "all", label: "Tất cả" },
  { key: "bodyweight", label: "Calisthenics" },
  { key: "strength", label: "Sức mạnh" },
  { key: "cardio", label: "Cardio" },
  { key: "resistance", label: "Kháng lực" },
] as const;

export type ShopCategory = (typeof SHOP_CATEGORIES)[number]["key"];

const PRODUCT_CATEGORY: Record<string, Exclude<ShopCategory, "all">> = {
  "parallel-bars": "bodyweight",
  "pull-up-bar": "bodyweight",
  "gymnastic-rings": "bodyweight",
  dumbbell: "strength",
  plate: "strength",
  "jump-rope": "cardio",
  "resistance-band": "resistance",
  "resistance-band-1": "resistance",
  "resistance-band-2": "resistance",
};

export function shopCategoryForSlug(slug: string): Exclude<ShopCategory, "all"> | "other" {
  return PRODUCT_CATEGORY[slug] || "other";
}

export function shopCategoryLabel(slug: string): string {
  const key = shopCategoryForSlug(slug);
  return SHOP_CATEGORIES.find((category) => category.key === key)?.label || "Dụng cụ tập luyện";
}

/** Homepage + shop merchandising: same 3 groups as gen-lịch wizard, by difficulty. */
export type HomeShopGroup = {
  id: WizardEquipmentGroupId;
  label_vi: string;
  difficulty: string;
  badge: string;
  hint: string;
  accentBar: string;
  tint: string;
  homeSurface: string;
  homeHover: string;
  homeArrow: string;
  href: string;
  products: readonly { slug: string; label_vi: string }[];
};

export const HOME_SHOP_GROUPS: HomeShopGroup[] = WIZARD_EQUIPMENT_GROUPS.map((group) => {
  const ui = EQUIPMENT_GROUP_UI[group.id];
  return {
    id: group.id,
    label_vi: group.label_vi,
    difficulty: ui.difficulty,
    badge: ui.badge,
    hint: ui.hint,
    accentBar: ui.accentBar,
    tint: ui.tint,
    homeSurface: ui.homeSurface,
    homeHover: ui.homeHover,
    homeArrow: ui.homeArrow,
    href: shopHrefForGroup(group.id),
    products: group.products?.length
      ? group.products
      : group.slugs.map((slug) => ({ slug, label_vi: group.label_vi })),
  };
});
