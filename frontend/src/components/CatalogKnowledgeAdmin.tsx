"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { getStoredUser } from "@/lib/auth";
import { difficultyLabel } from "@/lib/labels";
import {
  knowledgeArticlesApi,
  type KnowledgeArticleUpdate,
} from "@/lib/knowledgeArticlesApi";
import type { KnowledgeArticle } from "@/lib/types";

const LEVELS = ["beginner", "intermediate", "advanced"] as const;

type FormState = KnowledgeArticleUpdate & { slug: string };

const emptyForm: FormState = {
  slug: "",
  title_vi: "",
  content_md: "",
  level: "beginner",
  read_time_min: null,
  sort_order: 0,
  seo_title: "",
  seo_description: "",
  is_published: true,
};

function formFromArticle(row: KnowledgeArticle): FormState {
  const level = LEVELS.includes(row.level as (typeof LEVELS)[number]) ? row.level : row.level || "beginner";
  return {
    slug: row.slug,
    title_vi: row.title_vi,
    content_md: row.content_md || "",
    level,
    read_time_min: row.read_time_min,
    sort_order: row.sort_order ?? 0,
    seo_title: row.seo_title || "",
    seo_description: row.seo_description || "",
    is_published: row.is_published !== false,
  };
}

export default function CatalogKnowledgeAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<KnowledgeArticle[]>([]);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingArticle, setLoadingArticle] = useState(false);
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);
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
      const data = await knowledgeArticlesApi.adminList();
      setItems(data.items || []);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const rows = needle
      ? items.filter((row) => row.title_vi.toLowerCase().includes(needle) || row.slug.toLowerCase().includes(needle))
      : items;
    return [...rows].sort((a, b) => a.sort_order - b.sort_order || a.title_vi.localeCompare(b.title_vi, "vi"));
  }, [items, q]);

  async function startEdit(row: KnowledgeArticle) {
    setEditingId(row.id);
    setError("");
    setLoadingArticle(true);
    try {
      const full = await knowledgeArticlesApi.get(row.id);
      setForm(formFromArticle(full));
      setItems((prev) => prev.map((item) => (item.id === full.id ? { ...item, ...full } : item)));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoadingArticle(false);
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (editingId == null) return;
    setSaving(true);
    setError("");
    try {
      const minutes = form.read_time_min;
      const saved = await knowledgeArticlesApi.update(editingId, {
        title_vi: form.title_vi.trim(),
        content_md: form.content_md,
        level: form.level,
        read_time_min: minutes == null || Number.isNaN(minutes) ? null : Math.round(minutes),
        sort_order: Math.round(form.sort_order) || 0,
        seo_title: form.seo_title.trim(),
        seo_description: form.seo_description.trim(),
        is_published: form.is_published,
      });
      setItems((prev) => prev.map((item) => (item.id === saved.id ? { ...item, ...saved } : item)));
      setForm(formFromArticle(saved));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (!allowed) return null;

  const levelOptions = LEVELS.includes(form.level as (typeof LEVELS)[number])
    ? LEVELS
    : [form.level, ...LEVELS];

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Quản trị kho kiến thức</h1>
      <p className="mt-1 text-sm text-slate-500">Sửa bài đang hiện trên trang Kho kiến thức. Slug giữ nguyên để link cũ vẫn đúng.</p>

      <div className="mt-4">
        <input
          className="w-full max-w-sm rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm tiêu đề hoặc slug…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
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
                {visible.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.is_published ? "" : "opacity-60"}`}
                    onClick={() => void startEdit(row)}
                  >
                    <td className="px-3 py-2 font-medium">{row.title_vi}</td>
                    <td className="px-3 py-2">{row.is_published ? "Xuất bản" : "Ẩn"}</td>
                  </tr>
                ))}
                {!visible.length && (
                  <tr>
                    <td className="px-3 py-4 text-slate-400" colSpan={2}>
                      Không có bài khớp.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          )}
          <p className="border-t border-slate-100 px-3 py-2 text-xs text-slate-500">{visible.length} bài</p>
        </div>

        <form onSubmit={(e) => void save(e)} className="space-y-3 rounded-xl border border-slate-200 p-4">
          <h2 className="font-medium text-slate-800">{editingId == null ? "Chọn một bài" : `Sửa #${editingId}`}</h2>
          {loadingArticle && <p className="text-sm text-slate-400">Đang tải nội dung…</p>}
          <label className="block text-sm">
            Tiêu đề
            <input
              required
              disabled={editingId == null}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
              value={form.title_vi}
              onChange={(e) => setForm({ ...form, title_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Slug
            <input
              readOnly
              className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-500"
              value={form.slug}
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="block text-sm">
              Mức
              <select
                disabled={editingId == null}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
                value={form.level}
                onChange={(e) => setForm({ ...form, level: e.target.value })}
              >
                {levelOptions.map((level) => (
                  <option key={level} value={level}>
                    {difficultyLabel(level).vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Phút đọc
              <input
                type="number"
                min={0}
                disabled={editingId == null}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
                value={form.read_time_min ?? ""}
                onChange={(e) =>
                  setForm({
                    ...form,
                    read_time_min: e.target.value === "" ? null : Number(e.target.value),
                  })
                }
              />
            </label>
            <label className="block text-sm">
              Thứ tự
              <input
                type="number"
                disabled={editingId == null}
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
                value={form.sort_order}
                onChange={(e) => setForm({ ...form, sort_order: Number(e.target.value) })}
              />
            </label>
          </div>
          <label className="block text-sm">
            Tiêu đề SEO
            <input
              disabled={editingId == null}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
              value={form.seo_title}
              onChange={(e) => setForm({ ...form, seo_title: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Mô tả SEO
            <textarea
              disabled={editingId == null}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 disabled:bg-slate-50"
              rows={2}
              value={form.seo_description}
              onChange={(e) => setForm({ ...form, seo_description: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Nội dung (markdown)
            <textarea
              required
              disabled={editingId == null}
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 font-mono text-sm disabled:bg-slate-50"
              rows={14}
              value={form.content_md}
              onChange={(e) => setForm({ ...form, content_md: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              disabled={editingId == null}
              checked={form.is_published}
              onChange={(e) => setForm({ ...form, is_published: e.target.checked })}
            />
            Xuất bản (hiện trên kho kiến thức)
          </label>
          <button
            type="submit"
            disabled={saving || loadingArticle || editingId == null}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Đang lưu…" : "Lưu"}
          </button>
        </form>
      </div>
    </div>
  );
}
