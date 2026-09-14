"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { authApi } from "@/lib/authApi";
import { clearAuth } from "@/lib/auth";

export default function ChangePasswordForm() {
  const router = useRouter();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [err, setErr] = useState("");
  const [ok, setOk] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setOk("");
    if (newPassword !== confirm) {
      setErr("Mật khẩu mới không khớp.");
      return;
    }
    if (newPassword.length < 8) {
      setErr("Mật khẩu mới cần ít nhất 8 ký tự, gồm chữ và số.");
      return;
    }
    if (!/[A-Za-z]/.test(newPassword) || !/\d/.test(newPassword)) {
      setErr("Mật khẩu mới cần ít nhất 8 ký tự, gồm chữ và số.");
      return;
    }
    setLoading(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      setOk("Đã đổi mật khẩu. Vui lòng đăng nhập lại.");
      clearAuth();
      setTimeout(() => router.push("/dang-nhap?next=/tai-khoan"), 1200);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Đổi mật khẩu</h1>
        <p className="mt-1 text-sm text-slate-500">Sau khi đổi, bạn sẽ cần đăng nhập lại.</p>
      </div>
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {ok && <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700">{ok}</p>}
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mật khẩu hiện tại</label>
        <input
          type="password"
          required
          minLength={8}
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          className="field"
        />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mật khẩu mới</label>
        <input
          type="password"
          required
          minLength={8}
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="field"
        />
      </div>
      <div>
        <label className="mb-1.5 block text-sm font-semibold text-slate-600">Nhập lại mật khẩu mới</label>
        <input
          type="password"
          required
          minLength={8}
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          className="field"
        />
      </div>
      <button
        type="submit"
        disabled={loading}
        className="w-full rounded-xl bg-brand-500 py-3 font-bold text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {loading ? "Đang đổi…" : "Đổi mật khẩu"}
      </button>
    </form>
  );
}
