import ExerciseHub from "@/components/ExerciseHub";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Kho bài tập${BRAND_TITLE_SUFFIX}`,
  description: "Bài tập và dụng cụ tập luyện — kho tập của TAPTOT.",
};

export default function KhoBaiTapPage() {
  return <ExerciseHub />;
}
