"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { cookingPostsApi, type CookingPostPayload } from "@/lib/cookingPostsApi";
import { getStoredUser } from "@/lib/auth";
import { mediaUrl } from "@/lib/labels";
import { uploadAdminMedia } from "@/lib/shopApi";
import type { CookingPost } from "@/lib/types";

const emptyForm: CookingPostPayload = {
  title_vi: "",
  content_md: "",
  excerpt: "",
  cover_image_url: "",
  slug: "",
  is_published: false,
  sort_order: 0,
};

export default function CatalogCookingAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<CookingPost[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<CookingPostPayload>(emptyForm);
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
      const d = await cookingPostsApi.adminList({ page, page_size: 20, q });
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

  function startEdit(row: CookingPost) {
    setEditingId(row.id);
    setForm({
      title_vi: row.title_vi,
      content_md: row.content_md,
      excerpt: row.excerpt || "",
      cover_image_url: row.cover_image_url || "",
      slug: row.slug,
      is_published: row.is_published,
      sort_order: row.sort_order,
    });
  }

  async function onUpload(file: File) {
    setUploading(true);
    setError("");
    try {
      const url = await uploadAdminMedia(file);
      setForm((f) => ({ ...f, cover_image_url: url }));
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
      const body: CookingPostPayload = {
        ...form,
        excerpt: form.excerpt || null,
        cover_image_url: form.cover_image_url || null,
        slug: form.slug || null,
      };
      if (editingId == null) await cookingPostsApi.adminCreate(body);
      else await cookingPostsApi.adminUpdate(editingId, body);
      startCreate();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) return null;

  const cover = mediaUrl(form.cover_image_url);

  return (
    <div>
      <h1 className="text-2xl font-extrabold tracking-tight">Quản trị bài viết nấu ăn</h1>
      <p className="mt-1 text-sm text-slate-500">Bài xuất bản hiện trên trang chủ và mục Cách nấu món ăn ngon.</p>

      <div className="mt-4 flex flex-wrap gap-2">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm tiêu đề…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
        <button type="button" className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white" onClick={startCreate}>
          Bài mới
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
                  <th className="px-3 py-2">Tiêu đề</th>
                  <th className="px-3 py-2">Trạng thái</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.is_published ? "" : "opacity-60"}`}
                    onClick={() => startEdit(row)}
                  >
                    <td className="px-3 py-2 font-medium">{row.title_vi}</td>
                    <td className="px-3 py-2">{row.is_published ? "Xuất bản" : "Nháp"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
            <span>
              {total} bài · trang {page}/{pages}
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
          <h2 className="font-medium text-slate-800">{editingId == null ? "Bài mới" : `Sửa #${editingId}`}</h2>
          <label className="block text-sm">
            Tiêu đề
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.title_vi}
              onChange={(e) => setForm({ ...form, title_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Slug (để trống = tự tạo)
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.slug || ""}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Tóm tắt
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              rows={2}
              value={form.excerpt || ""}
              onChange={(e) => setForm({ ...form, excerpt: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Nội dung (markdown)
            <textarea
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm"
              rows={10}
              value={form.content_md}
              onChange={(e) => setForm({ ...form, content_md: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Ảnh bìa
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
              checked={!!form.is_published}
              onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
            />
            Xuất bản (hiện trên trang chủ / cách nấu)
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
