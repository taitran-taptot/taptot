"use client";

import Link from "next/link";
import { useState } from "react";
import { authApi } from "@/lib/authApi";

export default function ForgotPasswordForm() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    setLoading(true);
    try {
      const res = await authApi.forgotPassword(email);
      setMsg(res.message || "Nếu email tồn tại, hướng dẫn đặt lại mật khẩu đã được gửi.");
      if (res.reset_url) setResetUrl(res.reset_url);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Quên mật khẩu</h1>
        <p className="mt-1 text-sm text-slate-500">Nhập email đăng ký — chúng tôi gửi link đặt lại mật khẩu.</p>
      </div>
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {msg && <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700">{msg}</p>}
      {resetUrl && (
        <p className="rounded-xl bg-amber-50 px-3 py-2 text-xs text-amber-800">
          Dev mode: <Link href={resetUrl.replace(/^https?:\/\/[^/]+/, "")} className="underline break-all">{resetUrl}</Link>
        </p>
      )}
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Email</label>
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field" />
      </div>
      <button type="submit" disabled={loading} className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white hover:bg-brand-600 disabled:opacity-50">
        {loading ? "Đang gửi…" : "Gửi email đặt lại"}
      </button>
      <p className="text-center text-sm text-slate-500">
        <Link href="/dang-nhap" className="font-semibold text-brand-600 hover:underline">← Quay lại đăng nhập</Link>
      </p>
    </form>
  );
}
