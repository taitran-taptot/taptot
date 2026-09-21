"use client";

import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { Suspense, useState } from "react";
import { authApi } from "@/lib/authApi";

function ResetForm() {
  const sp = useSearchParams();
  const router = useRouter();
  const token = sp.get("token") || "";
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      setErr("Link không hợp lệ — thiếu token.");
      return;
    }
    try {
      await authApi.resetPassword(token, password);
      setOk(true);
      setTimeout(() => router.push("/dang-nhap"), 2000);
    } catch (ex) {
      setErr((ex as Error).message);
    }
  }

  if (!token) {
    return (
      <div className="mx-auto max-w-md rounded-2xl bg-white p-6 text-center shadow-soft">
        <p className="text-rose-600">Link đặt lại mật khẩu không hợp lệ.</p>
        <Link href="/quen-mat-khau" className="mt-4 inline-block font-semibold text-brand-600">Yêu cầu link mới</Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <h1 className="type-display">Đặt lại mật khẩu</h1>
      {err && <p className="text-sm text-rose-600">{err}</p>}
      {ok && <p className="text-sm text-brand-600">Đã đổi mật khẩu! Chuyển sang đăng nhập…</p>}
      <input
        type="password"
        required
        minLength={8}
        pattern="(?=.*[A-Za-z])(?=.*\d).{8,}"
        title="Ít nhất 8 ký tự, có chữ và số"
        placeholder="Mật khẩu mới (≥8 ký tự, gồm chữ và số)"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="field"
      />
      <button type="submit" className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white">Lưu mật khẩu</button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <section className="py-6">
      <Suspense fallback={<p className="text-center text-slate-400">Đang tải…</p>}>
        <ResetForm />
      </Suspense>
    </section>
  );
}
