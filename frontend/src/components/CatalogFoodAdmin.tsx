"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { adminFoodsApi, type AdminFood, type AdminFoodPayload } from "@/lib/adminFoodsApi";
import { api } from "@/lib/api";
import { getStoredUser } from "@/lib/auth";
import { mediaUrl } from "@/lib/labels";
import { uploadAdminMedia } from "@/lib/shopApi";
import type { FoodCategory } from "@/lib/types";

type FormState = {
  name_vi: string;
  name_en: string;
  category_id: number | "";
  serving_size: string;
  serving_grams: string;
  kcal_100g: string;
  protein_100g: string;
  carbs_100g: string;
  fat_100g: string;
  fiber_100g: string;
  sugar_100g: string;
  sodium_100mg: string;
  image_url: string;
  is_common: boolean;
  prep_state: string;
  status: string;
  slug: string;
};

const emptyForm: FormState = {
  name_vi: "",
  name_en: "",
  category_id: "",
  serving_size: "100g",
  serving_grams: "100",
  kcal_100g: "",
  protein_100g: "",
  carbs_100g: "",
  fat_100g: "",
  fiber_100g: "",
  sugar_100g: "",
  sodium_100mg: "",
  image_url: "",
  is_common: false,
  prep_state: "",
  status: "active",
  slug: "",
};

function numOrNull(raw: string): number | null {
  const t = raw.trim();
  if (!t) return null;
  const n = Number(t.replace(",", "."));
  return Number.isFinite(n) ? n : null;
}

function numOrZero(raw: string): number {
  return numOrNull(raw) ?? 0;
}

export default function CatalogFoodAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<AdminFood[]>([]);
  const [categories, setCategories] = useState<FoodCategory[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [q, setQ] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<number | "">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan");
      return;
    }
    setAllowed(true);
  }, [router]);

  useEffect(() => {
    if (!allowed) return;
    api
      .foodCategories()
      .then((d) => setCategories(d.items || []))
      .catch(() => {});
  }, [allowed]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await adminFoodsApi.list({
        page,
        page_size: 20,
        q,
        category_id: categoryFilter,
        status: statusFilter,
      });
      setItems(d.items || []);
      setTotal(d.total || 0);
      setPages(d.pages || 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, q, categoryFilter, statusFilter]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function startEdit(row: AdminFood) {
    setEditingId(row.id);
    setForm({
      name_vi: row.name_vi,
      name_en: row.name_en || "",
      category_id: row.category_id ?? "",
      serving_size: row.serving_size || "100g",
      serving_grams: row.serving_grams != null ? String(row.serving_grams) : "100",
      kcal_100g: row.kcal_100g != null ? String(row.kcal_100g) : "",
      protein_100g: row.protein_100g != null ? String(row.protein_100g) : "",
      carbs_100g: row.carbs_100g != null ? String(row.carbs_100g) : "",
      fat_100g: row.fat_100g != null ? String(row.fat_100g) : "",
      fiber_100g: row.fiber_100g != null ? String(row.fiber_100g) : "",
      sugar_100g: row.sugar_100g != null ? String(row.sugar_100g) : "",
      sodium_100mg: row.sodium_100mg != null ? String(row.sodium_100mg) : "",
      image_url: row.image_url || "",
      is_common: !!row.is_common,
      prep_state: row.prep_state || "",
      status: row.status || "active",
      slug: row.slug,
    });
  }

  async function onUpload(file: File) {
    setUploading(true);
    setError("");
    try {
      const url = await uploadAdminMedia(file);
      setForm((f) => ({ ...f, image_url: url }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  function payloadFromForm(): AdminFoodPayload {
    return {
      name_vi: form.name_vi.trim(),
      name_en: form.name_en.trim() || null,
      category_id: form.category_id === "" ? null : form.category_id,
      serving_size: form.serving_size.trim() || "100g",
      serving_grams: numOrZero(form.serving_grams) || 100,
      kcal_100g: numOrZero(form.kcal_100g),
      protein_100g: numOrZero(form.protein_100g),
      carbs_100g: numOrZero(form.carbs_100g),
      fat_100g: numOrZero(form.fat_100g),
      fiber_100g: numOrNull(form.fiber_100g),
      sugar_100g: numOrNull(form.sugar_100g),
      sodium_100mg: numOrNull(form.sodium_100mg),
      image_url: form.image_url.trim() || null,
      is_common: form.is_common,
      prep_state: form.prep_state || null,
      status: form.status || "active",
      slug: form.slug.trim() || null,
    };
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body = payloadFromForm();
      if (editingId == null) await adminFoodsApi.create(body);
      else await adminFoodsApi.update(editingId, body);
      startCreate();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const servingPreview = useMemo(() => {
    const grams = numOrZero(form.serving_grams) || 100;
    const kcal = numOrZero(form.kcal_100g);
    return Math.round((kcal * grams) / 10) / 10;
  }, [form.kcal_100g, form.serving_grams]);

  if (!allowed) return null;

  const cover = mediaUrl(form.image_url);
  const catName = Object.fromEntries(categories.map((c) => [c.id, c.name_vi]));

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Quản trị thức ăn</h1>
      <p className="mt-1 text-sm text-slate-500">
        Sửa tên, quầy, khẩu phần, calo theo 100g. Ẩn món thì thư viện `/thuc-an` không còn hiện.
      </p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm tên món…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={categoryFilter}
          onChange={(e) => {
            setPage(1);
            setCategoryFilter(e.target.value ? Number(e.target.value) : "");
          }}
        >
          <option value="">Mọi quầy</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name_vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={statusFilter}
          onChange={(e) => {
            setPage(1);
            setStatusFilter(e.target.value);
          }}
        >
          <option value="">Mọi trạng thái</option>
          <option value="active">Đang hiện</option>
          <option value="deprecated">Đã ẩn</option>
        </select>
        <button
          type="button"
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white"
          onClick={startCreate}
        >
          Món mới
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
                  <th className="px-3 py-2">Tên</th>
                  <th className="px-3 py-2">Quầy</th>
                  <th className="px-3 py-2">kcal/100g</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.status === "active" ? "" : "opacity-60"}`}
                    onClick={() => startEdit(row)}
                  >
                    <td className="px-3 py-2 font-medium">
                      {row.name_vi}
                      {row.status !== "active" && (
                        <span className="ml-2 text-xs font-normal text-slate-400">ẩn</span>
                      )}
                    </td>
                    <td className="px-3 py-2 text-slate-500">
                      {row.category_id != null ? catName[row.category_id] || "—" : "—"}
                    </td>
                    <td className="px-3 py-2">{row.kcal_100g ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
            <span>
              {total} món · trang {page}/{pages}
            </span>
            <span className="flex gap-2">
              <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Trước
              </button>
              <button type="button" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                Sau
              </button>
            </span>
          </div>
        </div>

        <form onSubmit={(e) => void save(e)} className="space-y-3 rounded-xl border border-slate-200 p-4">
          <h2 className="font-medium text-slate-800">{editingId == null ? "Món mới" : `Sửa #${editingId}`}</h2>
          <label className="block text-sm">
            Tên tiếng Việt
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_vi}
              onChange={(e) => setForm({ ...form, name_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Tên tiếng Anh
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_en}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Quầy
            <select
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.category_id}
              onChange={(e) =>
                setForm({ ...form, category_id: e.target.value ? Number(e.target.value) : "" })
              }
            >
              <option value="">Chưa chọn</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_vi}
                </option>
              ))}
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              Khẩu phần quen
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.serving_size}
                onChange={(e) => setForm({ ...form, serving_size: e.target.value })}
                placeholder="1 chén cơm"
              />
            </label>
            <label className="block text-sm">
              Gram / khẩu phần
              <input
                type="number"
                min={1}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.serving_grams}
                onChange={(e) => setForm({ ...form, serving_grams: e.target.value })}
              />
            </label>
          </div>
          <p className="text-xs font-semibold tracking-wide text-slate-400 uppercase">Theo 100g</p>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              Calo
              <input
                required
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.kcal_100g}
                onChange={(e) => setForm({ ...form, kcal_100g: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Đạm (g)
              <input
                required
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.protein_100g}
                onChange={(e) => setForm({ ...form, protein_100g: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Tinh bột (g)
              <input
                required
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.carbs_100g}
                onChange={(e) => setForm({ ...form, carbs_100g: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Chất béo (g)
              <input
                required
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.fat_100g}
                onChange={(e) => setForm({ ...form, fat_100g: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Xơ (g)
              <input
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.fiber_100g}
                onChange={(e) => setForm({ ...form, fiber_100g: e.target.value })}
              />
            </label>
            <label className="block text-sm">
              Đường (g)
              <input
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.sugar_100g}
                onChange={(e) => setForm({ ...form, sugar_100g: e.target.value })}
              />
            </label>
            <label className="col-span-2 block text-sm">
              Natri (mg)
              <input
                type="number"
                min={0}
                step="any"
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.sodium_100mg}
                onChange={(e) => setForm({ ...form, sodium_100mg: e.target.value })}
              />
            </label>
          </div>
          <p className="text-sm text-slate-500">
            Khẩu phần sẽ được tính tự động: <span className="font-semibold text-slate-700">{servingPreview} kcal</span>
          </p>
          <label className="block text-sm">
            Trạng thái sống / nấu
            <select
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.prep_state}
              onChange={(e) => setForm({ ...form, prep_state: e.target.value })}
            >
              <option value="">Không ghi</option>
              <option value="raw">Sống</option>
              <option value="cooked">Nấu</option>
              <option value="dry">Khô</option>
            </select>
          </label>
          <label className="block text-sm">
            Ảnh
            <input
              type="file"
              accept="image/*"
              className="mt-1 block w-full text-sm"
              disabled={uploading}
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void onUpload(f);
              }}
            />
          </label>
          {cover && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={cover} alt="" className="h-28 rounded-lg object-cover" />
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_common}
              onChange={(e) => setForm({ ...form, is_common: e.target.checked })}
            />
            Món quen (lên đầu quầy)
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.status === "active"}
              onChange={(e) => setForm({ ...form, status: e.target.checked ? "active" : "deprecated" })}
            />
            Hiện trên thư viện thực phẩm
          </label>
          {editingId == null && (
            <label className="block text-sm">
              Slug (để trống = tự tạo)
              <input
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.slug}
                onChange={(e) => setForm({ ...form, slug: e.target.value })}
              />
            </label>
          )}
          <button
            type="submit"
            disabled={saving || uploading}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Đang lưu…" : "Lưu"}
          </button>
        </form>
      </div>
    </div>
  );
}
