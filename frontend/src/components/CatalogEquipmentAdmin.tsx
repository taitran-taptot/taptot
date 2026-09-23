"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import {
  adminCatalogApi,
  type EquipmentPayload,
  type EquipmentRow,
} from "@/lib/adminCatalogApi";
import { getStoredUser } from "@/lib/auth";

const emptyForm: EquipmentPayload = {
  name_vi: "",
  name_en: "",
  slug: "",
  category: "",
  is_active: true,
  sort_order: 0,
  specs_vi: "",
};

export default function CatalogEquipmentAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<EquipmentRow[]>([]);
  const [q, setQ] = useState("");
  const [activeFilter, setActiveFilter] = useState("true");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<EquipmentPayload>(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await adminCatalogApi.equipment();
      setItems(res.items || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được danh sách dụng cụ");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((row) => {
      if (activeFilter === "true" && row.is_active === false) return false;
      if (activeFilter === "false" && row.is_active !== false) return false;
      if (!needle) return true;
      const blob = `${row.name_vi} ${row.slug} ${row.category || ""} ${row.specs_vi || ""}`.toLowerCase();
      return blob.includes(needle);
    });
  }, [items, q, activeFilter]);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function startEdit(row: EquipmentRow) {
    setEditingId(row.id);
    setForm({
      name_vi: row.name_vi,
      name_en: row.name_en || "",
      slug: row.slug,
      category: row.category || "",
      is_active: row.is_active !== false,
      sort_order: row.sort_order || 0,
      specs_vi: row.specs_vi || "",
    });
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name_vi.trim() || !form.slug.trim()) {
      setError("Cần tên tiếng Việt và slug.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const body: EquipmentPayload = {
        name_vi: form.name_vi.trim(),
        name_en: form.name_en?.trim() || null,
        slug: form.slug.trim(),
        category: form.category?.trim() || null,
        is_active: form.is_active,
        sort_order: Number(form.sort_order) || 0,
        specs_vi: form.specs_vi?.trim() || null,
      };
      if (editingId == null) await adminCatalogApi.createEquipment(body);
      else await adminCatalogApi.updateEquipment(editingId, body);
      startCreate();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) return null;

  return (
    <div>
      <h1 className="type-display">Quản trị dụng cụ</h1>
      <p className="mt-1 text-sm text-slate-500">
        Tên, slug, nhóm và thông số sản phẩm — GPT dùng khi lập lịch 100 ngày.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm tên, slug, thông số…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={activeFilter}
          onChange={(e) => setActiveFilter(e.target.value)}
        >
          <option value="">Active + ẩn</option>
          <option value="true">Đang hiện</option>
          <option value="false">Đã ẩn</option>
        </select>
        <button
          type="button"
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white"
          onClick={startCreate}
        >
          Thêm dụng cụ
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          {loading ? (
            <p className="p-6 text-sm text-slate-400">Đang tải…</p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Tên</th>
                  <th className="px-3 py-2">Nhóm</th>
                  <th className="px-3 py-2">Thông số</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.is_active ? "" : "opacity-50"}`}
                    onClick={() => startEdit(row)}
                  >
                    <td className="px-3 py-2 text-slate-400">{row.id}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-slate-800">{row.name_vi}</div>
                      <div className="text-xs text-slate-400">{row.slug}</div>
                    </td>
                    <td className="px-3 py-2">{row.category || "—"}</td>
                    <td className="max-w-[12rem] truncate px-3 py-2 text-slate-500">
                      {row.specs_vi || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
            {filtered.length} / {items.length} dụng cụ
          </div>
        </div>

        <form onSubmit={(e) => void save(e)} className="space-y-3 rounded-xl border border-slate-200 p-4">
          <h2 className="font-medium text-slate-800">
            {editingId == null ? "Dụng cụ mới" : `Sửa #${editingId}`}
          </h2>
          <label className="block text-sm">
            Tên VI
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_vi}
              onChange={(e) => setForm({ ...form, name_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Slug
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Nhóm
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.category || ""}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Thông số sản phẩm
            <textarea
              rows={6}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              placeholder="Ví dụ: bộ tạ đơn 50 kg, cặp đĩa 1,25–7,5 kg…"
              value={form.specs_vi || ""}
              onChange={(e) => setForm({ ...form, specs_vi: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Đang hiện
          </label>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Đang lưu…" : "Lưu"}
          </button>
        </form>
      </div>
    </div>
  );
}
