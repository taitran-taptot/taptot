import type { PlanDayInsight, PlanInsights } from "@/lib/plansApi";

export function dayInsightFor(
  insights: PlanInsights | null | undefined,
  dayNumber: number,
): PlanDayInsight | undefined {
  return insights?.days?.find((d) => d.day_number === dayNumber);
}

export function exerciseWhyFor(
  dayInsight: PlanDayInsight | undefined,
  exerciseId: number,
): string | undefined {
  return dayInsight?.exercises?.find((e) => e.exercise_id === exerciseId)?.why_vi;
}

export function mealWhyFor(
  dayInsight: PlanDayInsight | undefined,
  foodId: number,
  mealType: string,
): string | undefined {
  return dayInsight?.meals?.find((m) => m.food_id === foodId && m.meal_type === mealType)?.why_vi;
}
