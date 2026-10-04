import { Suspense } from "react";
import AccountWorkspace from "@/components/AccountWorkspace";

export const metadata = { title: "Tài khoản — TAPTOT" };

export default function TaiKhoanPage() {
  return (
    <Suspense fallback={<p className="py-10 text-center text-sm text-slate-400">Đang tải…</p>}>
      <AccountWorkspace />
    </Suspense>
  );
}
