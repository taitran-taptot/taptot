import { Suspense } from "react";
import ExerciseLibrary from "@/components/ExerciseLibrary";

export default function AccountExercisesPage() {
  return (
    <Suspense fallback={<div className="py-16 text-center text-slate-400">Đang tải…</div>}>
      <ExerciseLibrary />
    </Suspense>
  );
}
