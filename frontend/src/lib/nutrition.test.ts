import { describe, expect, it } from "vitest";
import { foundationWeightGoalCard } from "./nutrition";

describe("foundationWeightGoalCard", () => {
  it("obese loses toward normal BMI at a safe 2-month pace", () => {
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
    expect(card?.targetKg).toBeGreaterThanOrEqual(84);
    expect(card?.targetKg).toBeLessThanOrEqual(87);
    expect(card?.dailyKcal).toBeGreaterThanOrEqual(1500);
    expect(card?.copyVi).toContain("90 kg");
    expect(card?.copyVi).toContain("kcal/ngày");
    expect(card?.copyVi).toContain("2 tháng");
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
