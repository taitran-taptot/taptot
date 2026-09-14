import { Suspense } from "react";
import ExerciseLibrary from "@/components/ExerciseLibrary";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Kho bài tập${BRAND_TITLE_SUFFIX}`,
  description: "Kho bài tập lọc theo nhóm cơ và dụng cụ.",
};

export default function ExercisesPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-slate-400">Đang tải…</div>}>
      <ExerciseLibrary />
    </Suspense>
  );
}
