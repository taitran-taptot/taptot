"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { getStoredUser } from "@/lib/auth";
import {
  trainerClientsApi,
  type ClientInfoPayload,
  type TrainerClient,
} from "@/lib/phase3Api";

const GOAL_OPTS: { value: string; label: string }[] = [
  { value: "lose_weight", label: "Giảm cân" },
  { value: "maintain", label: "Giữ cân" },
  { value: "gain_muscle", label: "Tăng cơ" },
  { value: "gain_weight", label: "Tăng cân" },
];

const GENDER_OPTS: { value: string; label: string }[] = [
  { value: "male", label: "Nam" },
  { value: "female", label: "Nữ" },
];

function goalLabel(goal: string | null): string {
  return GOAL_OPTS.find((o) => o.value === goal)?.label || "—";
}

function genderLabel(gender: string | null): string {
  return GENDER_OPTS.find((o) => o.value === gender)?.label || "—";
}

interface DraftInfo {
  full_name: string;
  goal: string;
  gender: string;
  age: string;
  height_cm: string;
  weight_kg: string;
}

const EMPTY_DRAFT: DraftInfo = {
  full_name: "",
  goal: "",
  gender: "",
  age: "",
  height_cm: "",
  weight_kg: "",
};

function toDraft(c: TrainerClient): DraftInfo {
  return {
    full_name: c.full_name ?? "",
    goal: c.goal ?? "",
    gender: c.gender ?? "",
    age: c.age != null ? String(c.age) : "",
    height_cm: c.height_cm != null ? String(c.height_cm) : "",
    weight_kg: c.weight_kg != null ? String(c.weight_kg) : "",
  };
}

function draftToPayload(d: DraftInfo): ClientInfoPayload {
  const parse = (v: string): number | null => {
    const t = v.trim();
    if (!t) return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  };
  const ageRaw = parse(d.age);
  const height = parse(d.height_cm);
  const weight = parse(d.weight_kg);
  if (d.age.trim() && ageRaw == null) throw new Error("Tuổi không hợp lệ");
  if (d.height_cm.trim() && height == null) throw new Error("Chiều cao không hợp lệ");
  if (d.weight_kg.trim() && weight == null) throw new Error("Cân nặng không hợp lệ");
  if (ageRaw != null && (ageRaw < 10 || ageRaw > 100)) throw new Error("Tuổi phải từ 10–100");
  if (height != null && (height < 80 || height > 250)) throw new Error("Chiều cao phải từ 80–250 cm");
  if (weight != null && (weight < 20 || weight > 400)) throw new Error("Cân nặng phải từ 20–400 kg");
  return {
    full_name: d.full_name.trim() || null,
    goal: d.goal || null,
    gender: d.gender || null,
    age: ageRaw == null ? null : Math.round(ageRaw),
    height_cm: height,
    weight_kg: weight,
  };
}

function ClientInfoFields({
  draft,
  onChange,
  namePlaceholder,
}: {
  draft: DraftInfo;
  onChange: (partial: Partial<DraftInfo>) => void;
  namePlaceholder?: string;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Họ tên</span>
        <input
          className="field"
          value={draft.full_name}
          onChange={(e) => onChange({ full_name: e.target.value })}
          placeholder={namePlaceholder || "Tên khách hàng"}
        />
      </label>
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Mục tiêu</span>
        <select className="field" value={draft.goal} onChange={(e) => onChange({ goal: e.target.value })}>
          <option value="">— Chọn —</option>
          {GOAL_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Giới tính</span>
        <select
          className="field"
          value={draft.gender}
          onChange={(e) => onChange({ gender: e.target.value })}
        >
          <option value="">— Chọn —</option>
          {GENDER_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Tuổi</span>
        <input
          className="field"
          type="number"
          min={10}
          max={100}
          value={draft.age}
          onChange={(e) => onChange({ age: e.target.value })}
        />
      </label>
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Chiều cao (cm)</span>
        <input
          className="field"
          type="number"
          min={80}
          max={250}
          value={draft.height_cm}
          onChange={(e) => onChange({ height_cm: e.target.value })}
        />
      </label>
      <label className="space-y-1">
        <span className="text-xs font-semibold text-slate-600">Cân nặng (kg)</span>
        <input
          className="field"
          type="number"
          min={20}
          max={400}
          value={draft.weight_kg}
          onChange={(e) => onChange({ weight_kg: e.target.value })}
        />
      </label>
    </div>
  );
}

export default function TrainerClientsPanel() {
  const user = getStoredUser();
  const isTrainer = user?.role === "trainer" || user?.role === "admin";

  const [clients, setClients] = useState<TrainerClient[]>([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState<DraftInfo | null>(null);
  const [saving, setSaving] = useState(false);

  const [addEmail, setAddEmail] = useState("");
  const [addDraft, setAddDraft] = useState<DraftInfo>(EMPTY_DRAFT);
  const [adding, setAdding] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const rows = await trainerClientsApi.list();
      setClients(rows.filter((c) => c.status === "active"));
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isTrainer) void load();
    else setLoading(false);
  }, [isTrainer, load]);

  function startEdit(c: TrainerClient) {
    setEditingId(c.client_id);
    setDraft(toDraft(c));
    setErr("");
  }

  function cancelEdit() {
    setEditingId(null);
    setDraft(null);
  }

  function patchDraft(partial: Partial<DraftInfo>) {
    setDraft((prev) => (prev ? { ...prev, ...partial } : prev));
  }

  async function saveEdit(clientId: string) {
    if (!draft) return;
    setSaving(true);
    setErr("");
    try {
      const payload = draftToPayload(draft);
      const updated = await trainerClientsApi.updateInfo(clientId, payload);
      setClients((prev) => prev.map((c) => (c.client_id === clientId ? { ...c, ...updated } : c)));
      cancelEdit();
      setMsg("Đã cập nhật thông tin khách hàng.");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function onAddClient(e: React.FormEvent) {
    e.preventDefault();
    setAdding(true);
    setErr("");
    setMsg("");
    try {
      const info = draftToPayload(addDraft);
      const row = await trainerClientsApi.add(addEmail.trim(), info);
      setClients((prev) => [row, ...prev.filter((c) => c.client_id !== row.client_id)]);
      setAddEmail("");
      setAddDraft(EMPTY_DRAFT);
      setMsg(`Đã thêm khách hàng ${row.full_name || row.display_name || row.email || row.client_id}`);
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setAdding(false);
    }
  }

  if (!user) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Quản lý khách hàng</h1>
        <p className="mt-2 text-sm text-slate-500">Vui lòng đăng nhập bằng tài khoản huấn luyện viên.</p>
        <Link href="/dang-nhap" className="mt-4 inline-block font-semibold text-brand-600">
          Đăng nhập
        </Link>
      </section>
    );
  }

  if (!isTrainer) {
    return (
      <section className="mx-auto max-w-lg px-4 py-10 text-center">
        <h1 className="text-xl font-extrabold">Quản lý khách hàng</h1>
        <p className="mt-2 text-sm text-slate-500">Tài khoản không có quyền huấn luyện viên.</p>
      </section>
    );
  }

  return (
    <section className="mx-auto max-w-3xl space-y-5 px-4 py-8">
      <div>
        <h1 className="text-xl font-extrabold tracking-tight sm:text-2xl">Quản lý khách hàng</h1>
        <p className="mt-1 text-sm text-slate-500">
          Thêm khách hàng và nhập thông tin (mục tiêu, tuổi, giới tính, cân nặng…).
        </p>
      </div>

      {err && <p className="rounded-xl bg-rose-50 px-3 py-2 text-sm text-rose-600">{err}</p>}
      {msg && <p className="rounded-xl bg-brand-50 px-3 py-2 text-sm text-brand-700">{msg}</p>}

      <form onSubmit={(e) => void onAddClient(e)} className="space-y-4 rounded-2xl bg-white p-5 shadow-soft">
        <p className="text-sm font-semibold text-slate-700">Thêm khách hàng</p>
        <label className="block space-y-1.5">
          <span className="text-sm font-semibold text-slate-600">Email</span>
          <input
            className="field"
            type="email"
            value={addEmail}
            onChange={(e) => setAddEmail(e.target.value)}
            placeholder="email khách hàng đã đăng ký"
            required
          />
        </label>
        <div className="space-y-3 rounded-xl bg-slate-50 p-4">
          <p className="text-sm font-semibold text-slate-700">Thông tin khách hàng</p>
          <ClientInfoFields
            draft={addDraft}
            onChange={(partial) => setAddDraft((prev) => ({ ...prev, ...partial }))}
          />
        </div>
        <button
          type="submit"
          disabled={adding}
          className="w-full rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white disabled:opacity-50"
        >
          {adding ? "Đang thêm…" : "Thêm khách hàng"}
        </button>
      </form>

      {loading ? (
        <p className="text-sm text-slate-400">Đang tải…</p>
      ) : !clients.length ? (
        <div className="rounded-2xl bg-white p-6 text-center shadow-soft">
          <p className="text-sm text-slate-500">Chưa có khách hàng nào trong danh sách.</p>
        </div>
      ) : (
        <ul className="space-y-3">
          {clients.map((c) => {
            const isEditing = editingId === c.client_id;
            const name = c.full_name || c.display_name || "Khách hàng";
            return (
              <li key={c.client_id} className="rounded-2xl bg-white p-5 shadow-soft">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-bold text-slate-800">{name}</p>
                    <p className="truncate text-xs text-slate-400">{c.email}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-700">
                    {c.active_plans} lịch
                  </span>
                </div>

                {!isEditing || !draft ? (
                  <>
                    <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2 text-sm sm:grid-cols-4">
                      <div>
                        <dt className="text-xs text-slate-400">Mục tiêu</dt>
                        <dd className="font-semibold text-slate-700">{goalLabel(c.goal)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-400">Giới tính</dt>
                        <dd className="font-semibold text-slate-700">{genderLabel(c.gender)}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-400">Tuổi</dt>
                        <dd className="font-semibold text-slate-700">{c.age ?? "—"}</dd>
                      </div>
                      <div>
                        <dt className="text-xs text-slate-400">Cân nặng</dt>
                        <dd className="font-semibold text-slate-700">
                          {c.weight_kg != null ? `${c.weight_kg} kg` : "—"}
                        </dd>
                      </div>
                    </dl>
                    <button
                      type="button"
                      onClick={() => startEdit(c)}
                      className="mt-3 rounded-lg border border-brand-200 px-3 py-1.5 text-xs font-semibold text-brand-700 hover:bg-brand-50"
                    >
                      Sửa thông tin
                    </button>
                  </>
                ) : (
                  <div className="mt-4 space-y-3">
                    <ClientInfoFields
                      draft={draft}
                      onChange={patchDraft}
                      namePlaceholder={c.display_name || "Tên khách hàng"}
                    />
                    <div className="flex gap-2">
                      <button
                        type="button"
                        disabled={saving}
                        onClick={() => void saveEdit(c.client_id)}
                        className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
                      >
                        {saving ? "Đang lưu…" : "Lưu"}
                      </button>
                      <button
                        type="button"
                        onClick={cancelEdit}
                        className="rounded-lg px-4 py-2 text-sm font-semibold text-slate-500 hover:bg-slate-50"
                      >
                        Huỷ
                      </button>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}

      <p className="text-center text-xs text-slate-400">
        <Link href="/hlv" className="font-semibold text-brand-600">
          ← Giao lịch cho khách hàng
        </Link>
      </p>
    </section>
  );
}
