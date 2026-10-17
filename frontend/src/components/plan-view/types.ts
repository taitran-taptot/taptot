export type PlanViewTab = "train" | "meals" | "overview";

export const PLAN_VIEW_TABS: { id: PlanViewTab; label: string }[] = [
  { id: "overview", label: "Tổng quan" },
  { id: "train", label: "Lịch tập" },
  { id: "meals", label: "Lịch ăn" },
];
