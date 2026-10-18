import { describe, expect, it } from "vitest";
import {
  collapsePublicEquipmentKeys,
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
    expect(shopGroupForSlug("xa-don-va-vong-treo")).toBe("bar-and-rings");
    expect(shopGroupForSlug("ta-don")).toBe("dumbbell");
    expect(shopGroupForSlug("day-khang-luc")).toBe("resistance-band");
    expect(isWizardEquipmentSlug("bar-and-rings")).toBe(true);
    expect(isWizardEquipmentSlug("xa-don-va-vong-treo")).toBe(true);
    expect(isWizardEquipmentSlug("ta-don")).toBe(true);
    expect(collapsePublicEquipmentKeys(["ta-don", "day-khang-luc", "xa-don-va-vong-treo"])).toEqual([
      "dumbbell",
      "resistance-band",
      "pull-up-bar",
    ]);
    expect(shopSortIndex("bar-and-rings")).toBe(shopSortIndex("pull-up-bar"));
    expect(shopSortIndex("xa-don-va-vong-treo")).toBe(shopSortIndex("pull-up-bar"));
  });

  it("keeps gen/kho expansion: band family and bar+rings slugs", () => {
    expect(expandPublicEquipmentKeys(["resistance-band"])).toEqual([
      "resistance-band-2",
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
