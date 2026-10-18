import { describe, expect, it } from "vitest";
import {
  foundationWeightGoalCard,
  recapWithChallenge100DaysGoal,
  chipsWithChallenge100DaysGoal,
  formatPlanHeroRecapDisplay,
} from "./nutrition";

describe("foundationWeightGoalCard", () => {
  it("obese loses toward normal BMI at a safe 1-month pace", () => {
    const card = foundationWeightGoalCard({
      gender: "male",
      age: 30,
      heightCm: 170,
      weightKg: 90,
      activity: "light",
    });
    expect(card).not.toBeNull();
    expect(card?.goal).toBe("lose_weight");
    expect(card?.band).toBe("obese_2");
    expect(card?.currentKg).toBe(90);
    expect(card?.targetKg).toBeGreaterThanOrEqual(87.5);
    expect(card?.targetKg).toBeLessThanOrEqual(89);
    expect(card?.dailyKcal).toBeGreaterThanOrEqual(1500);
    expect(card?.copyVi).toContain("90 kg");
    expect(card?.copyVi).toContain("Do BMI của bạn đang là");
    expect(card?.copyVi).toContain("kcal/ngày");
    expect(card?.copyVi).toContain("1 tháng");
    expect(card?.copyVi).toContain("18,5–22,9");
    expect(card?.summaryVi).toMatch(/kcal\/ngày/);
  });

  it("underweight gains and normal maintains", () => {
    const gain = foundationWeightGoalCard({
      gender: "female",
      age: 25,
      heightCm: 160,
      weightKg: 42,
      activity: "light",
    });
    expect(gain).not.toBeNull();
    expect(gain?.goal).toBe("gain_weight");
    expect(gain?.targetKg).toBeGreaterThan(42);
    expect(gain?.copyVi).toContain("tăng");
    expect(gain?.copyVi).toContain("18,5–22,9");

    const keep = foundationWeightGoalCard({
      gender: "male",
      age: 25,
      heightCm: 170,
      weightKg: 65,
      activity: "light",
    });
    expect(keep).not.toBeNull();
    expect(keep?.goal).toBe("maintain");
    expect(keep?.targetKg).toBe(65);
    expect(keep?.copyVi).toContain("duy trì");
  });

  it("overweight uses the slower 0.5% weekly cut", () => {
    const card = foundationWeightGoalCard({
      gender: "male",
      age: 25,
      heightCm: 170,
      weightKg: 70,
      activity: "moderate",
    });
    expect(card).not.toBeNull();
    expect(card?.band).toBe("overweight");
    expect(card?.goal).toBe("lose_weight");
    expect(card?.targetKg).toBeLessThan(70);
    expect(card?.targetBmi).toBeGreaterThanOrEqual(18.5);
  });
});

describe("recapWithChallenge100DaysGoal", () => {
  it("replaces 14 tuần with wizard 100-day kg goal", () => {
    const recap =
      "Nam · 25 tuổi · 165 cm · 65 kg\nNhà · tạ đơn · 3 buổi/tuần × 60 phút · 14 tuần · Người mới (0–1 tháng)";
    const out = recapWithChallenge100DaysGoal(recap, {
      challenge: true,
      kgPerWeek: 0.5,
      goal: "lose_weight",
    });
    expect(out).toContain("Giảm 7,0kg trong 100 ngày");
    expect(out).not.toContain("14 tuần");
  });

  it("maps chip 14 tuần", () => {
    const chips = chipsWithChallenge100DaysGoal(["3 buổi/tuần", "14 tuần", "Người mới (0–1 tháng)"], {
      challenge: true,
      kgPerWeek: 0.4,
      goal: "gain_weight",
    });
    expect(chips).toContain("Tăng 6,0kg trong 100 ngày");
    expect(chips).not.toContain("14 tuần");
  });
});

describe("formatPlanHeroRecapDisplay", () => {
  it("splits recap into personal / schedule / goal lines", () => {
    const recap =
      "Nam · 25 tuổi · 165 cm · 75 kg\nNhà · tạ đơn · 3 buổi/tuần × 60 phút · Giảm 10,5kg trong 100 ngày · Người mới (0–1 tháng)";
    const out = formatPlanHeroRecapDisplay(recap);
    expect(out).toBe(
      [
        "Thông tin cá nhân: Nam · 25 tuổi · 165 cm · 75 kg",
        "Lịch tập: Tạ đơn · 3 buổi/tuần × 60 phút",
        "Mục tiêu: Giảm 10,5kg trong 100 ngày",
      ].join("\n"),
    );
  });
});
