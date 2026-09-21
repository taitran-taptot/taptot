"use client";

import { useEffect, useState } from "react";
import { completeAdminStepUp } from "@/lib/adminStepUp";
import { authApi } from "@/lib/authApi";

export default function AdminStepUpModal() {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const onAsk = () => {
      setPassword("");
      setErr("");
      setOpen(true);
    };
    window.addEventListener("taptot:admin-step-up", onAsk);
    return () => window.removeEventListener("taptot:admin-step-up", onAsk);
  }, []);

  if (!open) return null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setLoading(true);
    try {
      await authApi.confirmPassword(password);
      setOpen(false);
      completeAdminStepUp(true);
    } catch (ex) {
      setErr((ex as Error).message || "Không xác nhận được mật khẩu.");
    } finally {
      setLoading(false);
    }
  }

  function cancel() {
    setOpen(false);
    completeAdminStepUp(false);
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-900/40 p-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-3 rounded-2xl bg-white p-5 shadow-soft">
        <h2 className="text-lg font-bold tracking-tight">Xác nhận quản trị</h2>
        <p className="text-sm text-slate-500">Nhập lại mật khẩu để sửa catalog / shop.</p>
        {err ? <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p> : null}
        <input
          type="password"
          required
          autoFocus
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field"
          placeholder="Mật khẩu"
        />
        <div className="flex gap-2">
          <button
            type="button"
            onClick={cancel}
            className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold text-slate-600 hover:bg-slate-50"
          >
            Hủy
          </button>
          <button
            type="submit"
            disabled={loading}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
          >
            {loading ? "Đang xác nhận…" : "Xác nhận"}
          </button>
        </div>
      </form>
    </div>
  );
}
