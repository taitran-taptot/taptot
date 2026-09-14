"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { shopApi, uploadAdminMedia, type ShopProductPayload } from "@/lib/shopApi";
import type { ShopProduct } from "@/lib/types";

const emptyForm: ShopProductPayload = {
  name_vi: "",
  description_vi: "",
  price_vnd: 0,
  stock_qty: 0,
  image_url: "",
  slug: "",
  is_active: true,
};

export default function CatalogShopProductAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<ShopProduct[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<ShopProductPayload>(emptyForm);
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

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const d = await shopApi.adminListProducts({ page, q });
      setItems(d.items || []);
      setTotal(d.total || 0);
      setPages(d.pages || 1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [page, q]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  function startCreate() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function startEdit(row: ShopProduct) {
    setEditingId(row.id);
    setForm({
      name_vi: row.name_vi,
      description_vi: row.description_vi || "",
      price_vnd: row.price_vnd,
      stock_qty: row.stock_qty,
      image_url: row.image_url || "",
      slug: row.slug,
      is_active: row.is_active,
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

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const body: ShopProductPayload = {
        ...form,
        description_vi: form.description_vi || null,
        image_url: form.image_url || null,
        slug: form.slug || null,
      };
      if (editingId == null) await shopApi.adminCreateProduct(body);
      else await shopApi.adminUpdateProduct(editingId, body);
      startCreate();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) return null;
  const img = mediaUrl(form.image_url);

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Quản trị sản phẩm</h1>
      <p className="mt-1 text-sm text-slate-500">Sản phẩm hiện trên trang Mua dụng cụ. Nhập số lượng tồn kho.</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm sản phẩm…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
        <button type="button" className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white" onClick={startCreate}>
          Thêm sản phẩm
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
                  <th className="px-3 py-2">Giá</th>
                  <th className="px-3 py-2">Kho</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.is_active ? "" : "opacity-50"}`}
                    onClick={() => startEdit(row)}
                  >
                    <td className="px-3 py-2 font-medium">{row.name_vi}</td>
                    <td className="px-3 py-2">{formatVnd(row.price_vnd)}</td>
                    <td className="px-3 py-2">{row.stock_qty}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
            <span>
              {total} SP · trang {page}/{pages}
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
          <h2 className="font-medium text-slate-800">{editingId == null ? "Sản phẩm mới" : `Sửa #${editingId}`}</h2>
          <label className="block text-sm">
            Tên
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_vi}
              onChange={(e) => setForm({ ...form, name_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Mô tả
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              rows={3}
              value={form.description_vi || ""}
              onChange={(e) => setForm({ ...form, description_vi: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              Giá (VNĐ)
              <input
                required
                type="number"
                min={0}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.price_vnd}
                onChange={(e) => setForm({ ...form, price_vnd: Number(e.target.value) || 0 })}
              />
            </label>
            <label className="block text-sm">
              Tồn kho
              <input
                required
                type="number"
                min={0}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.stock_qty}
                onChange={(e) => setForm({ ...form, stock_qty: Number(e.target.value) || 0 })}
              />
            </label>
          </div>
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
          {img && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={img} alt="" className="h-28 rounded-lg object-cover" />
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Đang bán
          </label>
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
