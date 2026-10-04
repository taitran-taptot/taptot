import { describe, expect, it } from "vitest";
import {
  expandPublicEquipmentKeys,
  isWizardEquipmentSlug,
  shopSortIndex,
  toggleLibraryEquipmentFilter,
  WIZARD_EQUIPMENT_GROUPS,
} from "@/lib/equipmentCatalog";
import { shopGroupForSlug } from "@/lib/equipmentGroupUi";

describe("wizard shop kits", () => {
  it("maps the bar-and-rings shop slug onto the wizard group", () => {
    expect(shopGroupForSlug("bar-and-rings")).toBe("bar-and-rings");
    expect(isWizardEquipmentSlug("bar-and-rings")).toBe(true);
    expect(shopSortIndex("bar-and-rings")).toBe(shopSortIndex("pull-up-bar"));
  });

  it("keeps gen/kho expansion: band family and bar+rings slugs", () => {
    expect(expandPublicEquipmentKeys(["resistance-band"])).toEqual([
      "resistance-band-1",
      "resistance-band-2",
      "day-mini-band",
    ]);
    const bar = WIZARD_EQUIPMENT_GROUPS.find((g) => g.id === "bar-and-rings");
    expect(bar?.label_vi).toBe("Xà đơn treo tường và Vòng treo");
    expect(bar?.slugs).toEqual(["pull-up-bar", "gymnastic-rings"]);
  });

  it("toggles Gym without mixing in tạ đơn", () => {
    expect(toggleLibraryEquipmentFilter([], "gym")).toEqual(["gym"]);
    expect(toggleLibraryEquipmentFilter(["gym", "dumbbell"], "gym")).toEqual(["dumbbell"]);
    expect(toggleLibraryEquipmentFilter(["gym"], "dumbbell")).toEqual(["dumbbell", "gym"]);
  });
});
