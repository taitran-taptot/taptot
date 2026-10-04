import { Suspense } from "react";
import AccountWorkspace from "@/components/AccountWorkspace";

export const metadata = { title: "Quản trị — TAPTOT" };

export default function QuanTriPage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-sm text-slate-400">Đang tải…</p>}>
      <AccountWorkspace />
    </Suspense>
  );
}
