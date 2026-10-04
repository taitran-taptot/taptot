"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";
import { authApi } from "@/lib/authApi";
import { isAdmin } from "@/lib/auth";
import { safeNext } from "@/lib/safeNext";
import { brandRichText } from "@/components/brandRichText";

export default function LoginForm() {
  const router = useRouter();
  const search = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      const user = await authApi.loginAndSave(email, password);
      const fallback = isAdmin(user.role) ? "/tai-khoan/quan-tri" : "/tai-khoan";
      router.push(safeNext(search.get("next"), fallback));
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <div>
        <h1 className="type-display">Đăng nhập HLV / Admin</h1>
        <p className="mt-1 text-sm text-slate-500">Dành cho huấn luyện viên và quản trị {brandRichText("TAPTOT")}.</p>
      </div>
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field" />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mật khẩu</label>
        <input type="password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} className="field" />
      </div>
      <button type="submit" disabled={loading} className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white hover:bg-brand-600 disabled:opacity-50">
        {loading ? "Đang đăng nhập…" : "Đăng nhập"}
      </button>
      <p className="text-center text-sm text-slate-500">
        <Link href="/quen-mat-khau" className="font-semibold text-brand-600 hover:underline">Quên mật khẩu?</Link>
      </p>
    </form>
  );
}
