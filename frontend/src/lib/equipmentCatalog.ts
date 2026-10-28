/** Public home-equipment catalog: only these items appear in kho dụng cụ. */

import { isShopBarKitSlug, SHOP_KIT_BY_PATH } from "@/lib/shopRoutes";

export const PUBLIC_EQUIPMENT_KEYS = [
  "pull-up-bar",
  "dumbbell",
  "resistance-band",
  "gymnastic-rings",
] as const;

export const PUBLIC_EQUIPMENT_LABELS: Record<(typeof PUBLIC_EQUIPMENT_KEYS)[number], string> = {
  "pull-up-bar": "Xà đơn",
  dumbbell: "Tạ đơn",
  "resistance-band": "Dây kháng lực",
  "gymnastic-rings": "Vòng treo",
};

/** First photo in uploads/media/equipment/<slug>/ (thumbnail). Extra files in the folder show in the gallery. */
export const PUBLIC_EQUIPMENT_IMAGES: Partial<
  Record<(typeof PUBLIC_EQUIPMENT_KEYS)[number], string>
> = {
  "pull-up-bar": "equipment/pull-up-bar/xadon.png?v=20261022b",
  dumbbell: "equipment/dumbbell/tadon.png?v=20261022b",
  "resistance-band": "equipment/resistance-band-2/01.png",
  // ?v= busts browser cache after re-cropping the cover.
  "gymnastic-rings": "equipment/gymnastic-rings/vongtreo.png?v=20261022b",
};

/**
 * Gen-lịch wizard + public kho: only these 3 groups are selectable.
 */
export type WizardEquipmentGroupId = "dumbbell" | "bar-and-rings" | "resistance-band";

export type WizardEquipmentGroup = {
  id: WizardEquipmentGroupId;
  label_vi: string;
  /** Public keys stored in equipment_list when this group is selected. */
  slugs: readonly (typeof PUBLIC_EQUIPMENT_KEYS)[number][];
  /** Optional dual-product captions (bar + rings). */
  products?: readonly { slug: (typeof PUBLIC_EQUIPMENT_KEYS)[number]; label_vi: string }[];
};

/** Ordered by difficulty ascending for the gen-lịch wizard. */
export const WIZARD_EQUIPMENT_GROUPS: readonly WizardEquipmentGroup[] = [
  {
    id: "resistance-band",
    label_vi: "Dây kháng lực",
    slugs: ["resistance-band"],
  },
  {
    id: "dumbbell",
    label_vi: "Tạ đơn",
    slugs: ["dumbbell"],
  },
  {
    id: "bar-and-rings",
    label_vi: "Xà đơn treo tường và Vòng treo",
    slugs: ["pull-up-bar", "gymnastic-rings"],
    products: [
      { slug: "pull-up-bar", label_vi: "Xà đơn" },
      { slug: "gymnastic-rings", label_vi: "Vòng treo" },
    ],
  },
] as const;

const ORDER = new Map(PUBLIC_EQUIPMENT_KEYS.map((key, i) => [key, i]));
const WIZARD_GROUP_BY_SLUG = new Map<string, WizardEquipmentGroup>();
for (const group of WIZARD_EQUIPMENT_GROUPS) {
  for (const slug of group.slugs) WIZARD_GROUP_BY_SLUG.set(slug, group);
}

export function publicEquipmentImage(key: string): string | null {
  const pub = toPublicEquipmentKey(key);
  if (!pub) return null;
  return PUBLIC_EQUIPMENT_IMAGES[pub] ?? null;
}

/** Extra zoom for product shots that have large empty margins (e.g. Vòng treo). */
export function equipmentImageFitClass(slug: string | null | undefined): string {
  const key = slug ? toPublicEquipmentKey(slug) || slug : "";
  if (key === "gymnastic-rings") {
    // Source is already tightly cropped; mild scale keeps full rings visible.
    return "object-contain object-center scale-110";
  }
  return "object-contain";
}

export function isBandFamilySlug(key: string): boolean {
  return (
    key === "resistance-band" ||
    key === "resistance-band-1" ||
    key === "resistance-band-2" ||
    key === "day-mini-band"
  );
}

/** Map DB/legacy slugs onto the single public catalog key. */
export function toPublicEquipmentKey(slug: string): (typeof PUBLIC_EQUIPMENT_KEYS)[number] | null {
  const key = slug.trim();
  const shopKit = SHOP_KIT_BY_PATH[key];
  if (shopKit === "dumbbell") return "dumbbell";
  if (shopKit === "resistance-band" || isBandFamilySlug(key)) return "resistance-band";
  if (shopKit === "bar-and-rings" || isShopBarKitSlug(key)) return "pull-up-bar";
  if (ORDER.has(key as (typeof PUBLIC_EQUIPMENT_KEYS)[number])) {
    return key as (typeof PUBLIC_EQUIPMENT_KEYS)[number];
  }
  return null;
}

export function collapsePublicEquipmentKeys(slugs: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  for (const raw of slugs) {
    const key = toPublicEquipmentKey(raw);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(key);
  }
  return out;
}

/** Collapse selection to wizard groups (bar+rings → one chip). */
export function collapseToWizardEquipmentGroups(slugs: string[]): WizardEquipmentGroup[] {
  const keys = new Set(collapsePublicEquipmentKeys(slugs));
  return WIZARD_EQUIPMENT_GROUPS.filter((g) => g.slugs.some((s) => keys.has(s)));
}

export function wizardEquipmentGroupSelected(
  selectedKeys: Iterable<string>,
  group: WizardEquipmentGroup,
): boolean {
  const set = selectedKeys instanceof Set ? selectedKeys : new Set(selectedKeys);
  return group.slugs.some((s) => set.has(s));
}

/** Turn a wizard group on/off — combo always writes/removes every slug in the group. */
export function toggleWizardEquipmentGroup(
  selectedKeys: Iterable<string>,
  group: WizardEquipmentGroup,
): string[] {
  const set = new Set(collapsePublicEquipmentKeys([...selectedKeys]));
  const on = wizardEquipmentGroupSelected(set, group);
  for (const slug of group.slugs) {
    if (on) set.delete(slug);
    else set.add(slug);
  }
  // Keep stable wizard order.
  return WIZARD_EQUIPMENT_GROUPS.flatMap((g) => g.slugs.filter((s) => set.has(s)));
}

/** Ensure incomplete bar/rings drafts expand to both products when group is active. */
export function syncWizardEquipmentSelection(slugs: string[]): string[] {
  const set = new Set(collapsePublicEquipmentKeys(slugs));
  for (const group of WIZARD_EQUIPMENT_GROUPS) {
    if (wizardEquipmentGroupSelected(set, group)) {
      for (const slug of group.slugs) set.add(slug);
    }
  }
  return WIZARD_EQUIPMENT_GROUPS.flatMap((g) => g.slugs.filter((s) => set.has(s)));
}

/** Gen-lịch / search: one public band key uses the tube ngũ sắc catalog. */
export function expandPublicEquipmentKeys(slugs: string[]): string[] {
  const out: string[] = [];
  const seen = new Set<string>();
  let hasBand = false;
  for (const raw of slugs) {
    const key = raw.trim();
    if (!key) continue;
    if (isBandFamilySlug(key)) {
      hasBand = true;
      continue;
    }
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(key);
  }
  if (hasBand && !seen.has("resistance-band-2")) {
    seen.add("resistance-band-2");
    out.push("resistance-band-2");
  }
  return out;
}

export function isPublicEquipmentKey(key: string): boolean {
  return ORDER.has(key as (typeof PUBLIC_EQUIPMENT_KEYS)[number]);
}

export function isWizardEquipmentSlug(key: string): boolean {
  if (isShopBarKitSlug(key)) return true;
  const kit = SHOP_KIT_BY_PATH[key];
  if (kit === "dumbbell" || kit === "resistance-band") return true;
  const pub = toPublicEquipmentKey(key);
  return Boolean(pub && WIZARD_GROUP_BY_SLUG.has(pub));
}

/** Old public slug "resistance-band" split into type 1 (loop) and type 2 (tube). */
export function normalizePublicEquipmentSlug(slug: string): string[] {
  const key = toPublicEquipmentKey(slug);
  return key ? [key] : [];
}

export function shopSortIndex(slug: string): number {
  if (isShopBarKitSlug(slug)) return ORDER.get("pull-up-bar") ?? 999;
  const pub = toPublicEquipmentKey(slug);
  if (pub) return ORDER.get(pub) ?? 999;
  return 999;
}
