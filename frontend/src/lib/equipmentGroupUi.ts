/**
 * Shared difficulty UI for wizard equipment groups — used by gen-lịch picker,
 * homepage merchandising, and /mua-dung-cu shop filters.
 */
import {
  WIZARD_EQUIPMENT_GROUPS,
  type WizardEquipmentGroupId,
  isBandFamilySlug,
  toPublicEquipmentKey,
} from "@/lib/equipmentCatalog";

export type ShopEquipmentGroupFilter = "all" | WizardEquipmentGroupId;

export type EquipmentGroupUi = {
  difficulty: string;
  badge: string;
  tint: string;
  tintSelected: string;
  accentBar: string;
  cardSelected: string;
  cardHover: string;
  checkSelected: string;
  hint: string;
  /** Homepage merchandising card surface (rest + hover). */
  homeSurface: string;
  homeHover: string;
  homeArrow: string;
};

export const EQUIPMENT_GROUP_UI: Record<WizardEquipmentGroupId, EquipmentGroupUi> = {
  "resistance-band": {
    difficulty: "Dễ",
    badge: "badge-easy",
    tint: "bg-brand-50 ring-brand-100",
    tintSelected: "bg-brand-100 ring-brand-200",
    accentBar: "bg-brand-400",
    cardSelected:
      "border-brand-500 bg-gradient-to-r from-brand-100 to-brand-50 shadow-sm ring-2 ring-brand-300",
    cardHover: "hover:border-brand-300 hover:bg-brand-50/40",
    checkSelected: "bg-brand-500 text-white shadow-sm",
    hint: "Linh hoạt, dễ bắt đầu",
    homeSurface:
      "border-brand-200/90 bg-gradient-to-br from-brand-50 via-white to-emerald-50/70 shadow-sm shadow-brand-100/40",
    homeHover:
      "hover:-translate-y-1 hover:border-brand-400 hover:shadow-lg hover:shadow-brand-200/50 hover:ring-2 hover:ring-brand-200",
    homeArrow: "text-brand-500 group-hover:text-brand-700",
  },
  dumbbell: {
    difficulty: "Trung bình",
    badge: "badge-mid",
    tint: "bg-amber-50 ring-amber-100",
    tintSelected: "bg-amber-100 ring-amber-200",
    accentBar: "bg-amber-400",
    cardSelected:
      "border-amber-500 bg-gradient-to-r from-amber-100 to-amber-50 shadow-sm ring-2 ring-amber-300",
    cardHover: "hover:border-amber-300 hover:bg-amber-50/40",
    checkSelected: "bg-amber-500 text-white shadow-sm",
    hint: "Đa dạng bài tập, cảm nhận cơ thể",
    homeSurface:
      "border-amber-200/90 bg-gradient-to-br from-amber-50 via-white to-orange-50/70 shadow-sm shadow-amber-100/40",
    homeHover:
      "hover:-translate-y-1 hover:border-amber-400 hover:shadow-lg hover:shadow-amber-200/50 hover:ring-2 hover:ring-amber-200",
    homeArrow: "text-amber-500 group-hover:text-amber-700",
  },
  "bar-and-rings": {
    difficulty: "Nâng cao",
    badge: "badge-hard",
    tint: "bg-rose-50 ring-rose-100",
    tintSelected: "bg-rose-100 ring-rose-200",
    accentBar: "bg-rose-400",
    cardSelected:
      "border-rose-500 bg-gradient-to-r from-rose-100 to-rose-50 shadow-sm ring-2 ring-rose-300",
    cardHover: "hover:border-rose-300 hover:bg-rose-50/40",
    checkSelected: "bg-rose-500 text-white shadow-sm",
    hint: "Kết hợp sức mạnh, sự dẻo dai",
    homeSurface:
      "border-rose-200/90 bg-gradient-to-br from-rose-50 via-white to-pink-50/70 shadow-sm shadow-rose-100/40",
    homeHover:
      "hover:-translate-y-1 hover:border-rose-400 hover:shadow-lg hover:shadow-rose-200/50 hover:ring-2 hover:ring-rose-200",
    homeArrow: "text-rose-500 group-hover:text-rose-700",
  },
};

const GROUP_BY_PUBLIC_SLUG = new Map<string, WizardEquipmentGroupId>();
for (const group of WIZARD_EQUIPMENT_GROUPS) {
  for (const slug of group.slugs) GROUP_BY_PUBLIC_SLUG.set(slug, group.id);
}

/** Map product/equipment slug → wizard group id, or "other". */
export function shopGroupForSlug(slug: string): WizardEquipmentGroupId | "other" {
  if (isBandFamilySlug(slug)) return "resistance-band";
  const pub = toPublicEquipmentKey(slug);
  if (pub && GROUP_BY_PUBLIC_SLUG.has(pub)) return GROUP_BY_PUBLIC_SLUG.get(pub)!;
  return "other";
}

export function isWizardEquipmentGroupId(value: string): value is WizardEquipmentGroupId {
  return WIZARD_EQUIPMENT_GROUPS.some((g) => g.id === value);
}

/** Legacy shop category → wizard group (for old ?category= links). */
const LEGACY_CATEGORY_TO_GROUP: Record<string, WizardEquipmentGroupId> = {
  resistance: "resistance-band",
  strength: "dumbbell",
  bodyweight: "bar-and-rings",
};

export function resolveShopGroupFilter(
  groupParam?: string | null,
  categoryParam?: string | null,
): ShopEquipmentGroupFilter {
  if (groupParam && isWizardEquipmentGroupId(groupParam)) return groupParam;
  if (categoryParam && LEGACY_CATEGORY_TO_GROUP[categoryParam]) {
    return LEGACY_CATEGORY_TO_GROUP[categoryParam];
  }
  return "all";
}

export function shopHrefForGroup(
  groupId: WizardEquipmentGroupId,
  opts?: { account?: boolean },
): string {
  const base = opts?.account ? "/tai-khoan/mua-dung-cu" : "/mua-dung-cu";
  return `${base}?group=${encodeURIComponent(groupId)}#danh-sach-san-pham`;
}

export function shopDifficultyLabel(slug: string): { vi: string; badge: string } {
  const groupId = shopGroupForSlug(slug);
  if (groupId === "other") return { vi: "Khác", badge: "badge-mid" };
  const ui = EQUIPMENT_GROUP_UI[groupId];
  return { vi: ui.difficulty, badge: ui.badge };
}
