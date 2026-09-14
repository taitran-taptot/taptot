import { Suspense } from "react";
import LoginForm from "@/components/LoginForm";

export const metadata = { title: "Đăng nhập — TAPTOT" };

export default function LoginPage() {
  return (
    <section className="py-6">
      <Suspense fallback={<div className="mx-auto max-w-md rounded-2xl bg-white p-6 text-sm text-slate-500 shadow-soft">Đang tải…</div>}>
        <LoginForm />
      </Suspense>
    </section>
  );
}
