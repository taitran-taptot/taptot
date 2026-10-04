import { describe, expect, it } from "vitest";
import {
  FAMILIARIZATION_HERO_RECAP_VI,
  FAMILIARIZATION_MISSION_VI,
  familiarizationNutritionVi,
  familiarizationOutcomeVi,
  familiarizationWeightGoalCopyVi,
} from "./familiarizationOverviewCopy";

describe("familiarizationOverviewCopy", () => {
  it("uses the new mission and gender-specific outcomes", () => {
    expect(FAMILIARIZATION_MISSION_VI).toContain("nhập môn");
    expect(FAMILIARIZATION_MISSION_VI).toContain("toàn thân");
    expect(FAMILIARIZATION_MISSION_VI).toContain("\n");
    expect(FAMILIARIZATION_MISSION_VI).toContain("Tuần 3 bắt đầu kéo người nằm");
    expect(FAMILIARIZATION_MISSION_VI).toContain("tuần 9 kiểm tra đầu ra");
    expect(FAMILIARIZATION_MISSION_VI).not.toContain("gia cố khớp");
    expect(familiarizationOutcomeVi("female")).toContain("Chống đẩy quỳ 4–10");
    expect(familiarizationOutcomeVi("male")).toContain("Chống đẩy sàn 3–8");
    expect(familiarizationOutcomeVi("female").split("\n").length).toBeGreaterThanOrEqual(6);
    expect(familiarizationOutcomeVi("female")).toContain("TAPTOT");
  });

  it("exposes the fixed hero recap for office beginners", () => {
    expect(FAMILIARIZATION_HERO_RECAP_VI).toContain("văn phòng");
    expect(FAMILIARIZATION_HERO_RECAP_VI).toContain("chưa có kinh nghiệm tập luyện");
  });

  it("rebuilds nutrition from weight goal fields", () => {
    const copy = familiarizationWeightGoalCopyVi({
      bmi: 26.7,
      band: "obese_1",
      band_vi: "Béo phì độ I",
      goal: "lose_weight",
      current_kg: 65,
      target_kg: 61,
      target_bmi: 25.1,
      weeks: 8,
      daily_kcal: 1200,
      protein_g: 110,
      copy_vi: "old",
    });
    expect(copy).toContain("Do BMI của bạn đang là béo phì độ i.\n");
    expect(copy).toContain("65 kg");
    expect(copy).toContain("1.200 kcal/ngày");
    expect(copy).not.toContain("đạm");
    expect(copy).toContain("61 kg");
    const nutrition = familiarizationNutritionVi({
      bmi: 26.7,
      band: "obese_1",
      band_vi: "Béo phì độ I",
      goal: "lose_weight",
      current_kg: 65,
      target_kg: 61,
      target_bmi: 25.1,
      weeks: 8,
      daily_kcal: 1200,
      protein_g: 110,
      copy_vi: "old",
    });
    expect(nutrition).toContain("Nạp đủ đạm");
    expect(nutrition).toContain("\nNgày nghỉ đi bộ nhẹ");
  });
});
