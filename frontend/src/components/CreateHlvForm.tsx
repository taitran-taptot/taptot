"use client";

import { useState } from "react";
import { authApi } from "@/lib/authApi";

export default function CreateHlvForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function createHlv(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    setCreating(true);
    try {
      const created = await authApi.createStaff(email, password, displayName);
      setMsg(`Đã tạo HLV ${created.email}.`);
      setEmail("");
      setPassword("");
      setDisplayName("");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setCreating(false);
    }
  }

  return (
    <form onSubmit={(e) => void createHlv(e)} className="space-y-3 rounded-2xl bg-white p-5 shadow-soft">
      <h1 className="type-display">Tạo tài khoản HLV</h1>
      <p className="text-sm text-slate-500">Không công khai — chỉ Admin thêm huấn luyện viên.</p>
      {msg && <p className="rounded-xl bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{msg}</p>}
      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      <label className="block text-sm font-semibold text-slate-600">
        Tên hiển thị
        <input required value={displayName} onChange={(e) => setDisplayName(e.target.value)} className="field mt-1" />
      </label>
      <label className="block text-sm font-semibold text-slate-600">
        Email
        <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="field mt-1" />
      </label>
      <label className="block text-sm font-semibold text-slate-600">
        Mật khẩu
        <input
          type="password"
          required
          minLength={8}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field mt-1"
        />
      </label>
      <button
        type="submit"
        disabled={creating}
        className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {creating ? "Đang tạo…" : "Tạo HLV"}
      </button>
    </form>
  );
}
