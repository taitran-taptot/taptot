"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { KnowledgeArticle } from "@/lib/types";
import type { PlanClientProfile, StaffKnowledgeRef } from "@/lib/plansApi";

const GENDER_OPTS = [
  { id: "", label: "Không nêu" },
  { id: "male", label: "Nam" },
  { id: "female", label: "Nữ" },
] as const;

export default function PlanOverviewEditor({
  summaryVi,
  onSummary,
  descriptionVi,
  onDescription,
  client,
  onClient,
  knowledge,
  onKnowledge,
}: {
  summaryVi: string;
  onSummary: (v: string) => void;
  descriptionVi: string;
  onDescription: (v: string) => void;
  client: PlanClientProfile;
  onClient: (next: PlanClientProfile) => void;
  knowledge: StaffKnowledgeRef[];
  onKnowledge: (next: StaffKnowledgeRef[]) => void;
}) {
  const [q, setQ] = useState("");
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .knowledgeArticles()
      .then((d) => setArticles(d.items || []))
      .catch(() => setArticles([]))
      .finally(() => setLoading(false));
  }, []);

  const selected = useMemo(() => new Set(knowledge.map((k) => k.slug)), [knowledge]);
  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    if (!needle) return articles.slice(0, 12);
    return articles
      .filter(
        (a) =>
          a.title_vi.toLowerCase().includes(needle) || a.slug.toLowerCase().includes(needle),
      )
      .slice(0, 12);
  }, [articles, q]);

  function toggle(article: KnowledgeArticle) {
    if (selected.has(article.slug)) {
      onKnowledge(knowledge.filter((k) => k.slug !== article.slug));
      return;
    }
    onKnowledge([...knowledge, { slug: article.slug, title_vi: article.title_vi }]);
  }

  return (
    <div className="space-y-4">
      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Hồ sơ khách</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-semibold text-slate-600">
            Chiều cao (cm)
            <input
              type="number"
              min={50}
              max={250}
              value={client.height_cm ?? ""}
              onChange={(e) =>
                onClient({
                  ...client,
                  height_cm: e.target.value === "" ? null : Number(e.target.value),
                })
              }
              className="field mt-1"
            />
          </label>
          <label className="text-sm font-semibold text-slate-600">
            Cân nặng (kg)
            <input
              type="number"
              min={20}
              max={400}
              step={0.1}
              value={client.weight_kg ?? ""}
              onChange={(e) =>
                onClient({
                  ...client,
                  weight_kg: e.target.value === "" ? null : Number(e.target.value),
                })
              }
              className="field mt-1"
            />
          </label>
          <label className="text-sm font-semibold text-slate-600">
            Giới tính
            <select
              value={client.gender || ""}
              onChange={(e) =>
                onClient({
                  ...client,
                  gender: (e.target.value || null) as PlanClientProfile["gender"],
                })
              }
              className="field mt-1"
            >
              {GENDER_OPTS.map((g) => (
                <option key={g.id || "none"} value={g.id}>
                  {g.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="mt-3 block text-sm font-semibold text-slate-600">
          Ghi chú
          <textarea
            value={client.notes || ""}
            onChange={(e) => onClient({ ...client, notes: e.target.value })}
            rows={3}
            className="field mt-1"
            placeholder="Chấn thương, giờ tập, sở thích…"
          />
        </label>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Lời HLV</p>
        <label className="mt-3 block text-sm font-semibold text-slate-600">
          Mô tả ngắn
          <input
            value={descriptionVi}
            onChange={(e) => onDescription(e.target.value)}
            className="field mt-1"
            placeholder="Một câu giới thiệu lịch này"
          />
        </label>
        <label className="mt-3 block text-sm font-semibold text-slate-600">
          Tổng quan (khách đọc trên /lich/…)
          <textarea
            value={summaryVi}
            onChange={(e) => onSummary(e.target.value)}
            rows={6}
            className="field mt-1 min-h-[8rem]"
            placeholder="Viết mục tiêu, lưu ý, cách dùng lịch…"
          />
        </label>
      </div>

      <div className="rounded-2xl bg-white p-4 shadow-soft">
        <p className="text-sm font-bold text-slate-700">Kiến thức nên đọc</p>
        <p className="mt-0.5 text-xs text-slate-400">Gán bài kho kiến thức — khách xem link trên trang chia sẻ.</p>
        {knowledge.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1.5">
            {knowledge.map((k) => (
              <li key={k.slug}>
                <button
                  type="button"
                  onClick={() => onKnowledge(knowledge.filter((x) => x.slug !== k.slug))}
                  className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-semibold text-brand-800 hover:bg-brand-100"
                >
                  {k.title_vi || k.slug} ×
                </button>
              </li>
            ))}
          </ul>
        )}
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          type="search"
          placeholder="Tìm bài kiến thức…"
          className="field mt-3"
        />
        {loading && <p className="mt-2 text-xs text-slate-400">Đang tải kho kiến thức…</p>}
        <ul className="mt-2 max-h-48 space-y-1 overflow-y-auto">
          {filtered.map((a) => {
            const on = selected.has(a.slug);
            return (
              <li key={a.slug}>
                <button
                  type="button"
                  onClick={() => toggle(a)}
                  className={`flex w-full items-center justify-between rounded-lg px-2.5 py-2 text-left text-sm ${
                    on ? "bg-brand-50 font-semibold text-brand-800" : "bg-slate-50 hover:bg-brand-50"
                  }`}
                >
                  <span className="truncate">{a.title_vi}</span>
                  <span className="shrink-0 text-xs">{on ? "Đã gán" : "+ Gán"}</span>
                </button>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}
