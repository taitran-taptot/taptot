import { Suspense } from "react";
import RegisterForm from "@/components/RegisterForm";

export const metadata = { title: "Đăng ký — TAPTOT" };

export default function RegisterPage() {
  return (
    <section className="py-6">
      <Suspense fallback={<div className="mx-auto max-w-md rounded-2xl bg-white p-6 text-sm text-slate-500 shadow-soft">Đang tải…</div>}>
        <RegisterForm />
      </Suspense>
    </section>
  );
}
