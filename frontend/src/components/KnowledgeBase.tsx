"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import type { KnowledgeArticle } from "@/lib/types";

const LEVEL_META: Record<string, { vi: string; order: number; badge: string }> = {
  beginner: { vi: "Cơ bản", order: 1, badge: "badge-easy" },
  basic: { vi: "Cơ bản", order: 1, badge: "badge-easy" },
  intermediate: { vi: "Trung cấp", order: 2, badge: "badge-mid" },
  advanced: { vi: "Nâng cao", order: 3, badge: "badge-hard" },
};

const LEVEL_SECTIONS = [
  {
    key: "co-ban" as const,
    label: "Cơ bản",
    badge: "badge-easy",
    desc: "Nền tảng tập & ăn cho người mới — mục tiêu, calo và thói quen vừa sức.",
    tone: "light" as const,
  },
  {
    key: "trung-cap" as const,
    label: "Trung cấp",
    badge: "badge-mid",
    desc: "Hiểu sâu hơn về lịch tập, tiến bộ và cách điều chỉnh khi đã quen.",
    tone: "warm" as const,
  },
  {
    key: "nang-cao" as const,
    label: "Nâng cao",
    badge: "badge-hard",
    desc: "Tối ưu hiệu suất, phục hồi và các chủ đề chuyên sâu hơn.",
    tone: "green" as const,
  },
];

function levelMeta(level: string) {
  return LEVEL_META[level] || { vi: level, order: 99, badge: "badge-gray" };
}

function levelBucket(level: string): (typeof LEVEL_SECTIONS)[number]["key"] {
  if (level === "advanced") return "nang-cao";
  if (level === "intermediate") return "trung-cap";
  return "co-ban";
}

/** Keep numbering from title (e.g. "1.0 — Mục tiêu"). */
function numberedTitle(title: string) {
  return title.replace(/\s*[—–]\s*/, " — ").trim();
}

function articleNumber(title: string) {
  const m = /^(\d+\.\d+)\s*/.exec(title);
  return m?.[1] ?? null;
}

function sortArticles(list: KnowledgeArticle[]) {
  return [...list].sort(
    (a, b) =>
      levelMeta(a.level).order - levelMeta(b.level).order ||
      (a.sort_order || 0) - (b.sort_order || 0) ||
      a.id - b.id,
  );
}

function cardTone(tone: "light" | "warm" | "green") {
  if (tone === "warm") return "bg-gradient-to-br from-orange-50 to-amber-50 ring-1 ring-orange-100";
  if (tone === "green") return "bg-gradient-to-br from-brand-50 to-emerald-50 ring-1 ring-brand-100";
  return "bg-white ring-1 ring-slate-100";
}

export default function KnowledgeBase() {
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [articleLoading, setArticleLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({
    "co-ban": false,
    "trung-cap": false,
    "nang-cao": false,
  });
  const deepLinkHandled = useRef(false);

  useEffect(() => {
    api
      .knowledgeArticles()
      .then((a) => setArticles(sortArticles((a.items || []).filter((x) => x.is_published !== false))))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const articlesByLevel = useMemo(() => {
    const map: Record<(typeof LEVEL_SECTIONS)[number]["key"], KnowledgeArticle[]> = {
      "co-ban": [],
      "trung-cap": [],
      "nang-cao": [],
    };
    for (const article of articles) {
      map[levelBucket(article.level)].push(article);
    }
    for (const key of Object.keys(map) as (typeof LEVEL_SECTIONS)[number]["key"][]) {
      map[key].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.id - b.id);
    }
    return map;
  }, [articles]);

  const selected = useMemo(
    () => articles.find((a) => a.id === selectedId) ?? null,
    [articles, selectedId],
  );

  function toggleSection(key: string) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function openLevel(key: (typeof LEVEL_SECTIONS)[number]["key"]) {
    setSelectedId(null);
    setOpenSections((prev) => ({ ...prev, [key]: true }));
    const first = articlesByLevel[key][0];
    if (first) selectArticle(first);
  }

  function selectArticle(article: KnowledgeArticle) {
    setSelectedId(article.id);
    const bucket = levelBucket(article.level);
    setOpenSections((prev) => ({ ...prev, [bucket]: true }));
    if (article.content_md && article.content_md.length > 80) return;
    setArticleLoading(true);
    api
      .knowledgeArticle(article.id)
      .then((full) => {
        setArticles((prev) => prev.map((row) => (row.id === full.id ? { ...row, ...full } : row)));
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setArticleLoading(false));
  }

  useEffect(() => {
    if (deepLinkHandled.current || loading || articles.length === 0) return;
    const qs = new URLSearchParams(window.location.search);
    const slug = (qs.get("bai") || qs.get("slug") || "").trim();
    if (!slug) {
      deepLinkHandled.current = true;
      return;
    }
    const match = articles.find((a) => a.slug === slug);
    deepLinkHandled.current = true;
    if (match) selectArticle(match);
  }, [loading, articles]);

  function showOverview() {
    setSelectedId(null);
  }

  return (
    <div className="space-y-10 pb-4">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Học & hiểu</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Kho kiến thức
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Bài viết từ cơ bản đến nâng cao, dễ hiểu cho người Việt — chọn mức bên dưới rồi đọc theo lộ trình.
        </p>
      </header>

      {error && (
        <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-600 ring-1 ring-rose-100">
          Lỗi tải dữ liệu: {error}
        </div>
      )}

      {loading ? (
        <div className="space-y-5">
          <div className="grid gap-5 lg:grid-cols-3">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-44 animate-pulse rounded-3xl bg-white shadow-soft" />
            ))}
          </div>
          <div className="flex flex-col gap-4 lg:flex-row">
            <div className="h-80 w-full animate-pulse rounded-3xl bg-white shadow-soft lg:w-72" />
            <div className="min-h-80 flex-1 animate-pulse rounded-3xl bg-white shadow-soft" />
          </div>
        </div>
      ) : articles.length === 0 ? (
        <div className="rounded-3xl bg-white py-16 text-center text-slate-400 shadow-soft ring-1 ring-slate-100">
          <p className="font-medium">Chưa có bài viết</p>
        </div>
      ) : (
        <>
          {selectedId == null && (
            <div className="grid gap-5 lg:grid-cols-3">
              {LEVEL_SECTIONS.map((section) => {
                const items = articlesByLevel[section.key];
                return (
                  <section
                    key={section.key}
                    className={`flex flex-col rounded-3xl p-6 shadow-soft sm:p-7 ${cardTone(section.tone)}`}
                  >
                    <div className="flex items-center gap-2">
                      <span className={`badge ${section.badge}`}>{section.label}</span>
                      <span className="text-xs font-medium text-slate-400">{items.length} bài</span>
                    </div>
                    <h2 className="mt-3 text-xl font-extrabold tracking-tight text-slate-900">
                      {section.label}
                    </h2>
                    <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{section.desc}</p>
                    <button
                      type="button"
                      onClick={() => openLevel(section.key)}
                      disabled={!items.length}
                      className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {items.length ? `Vào mục ${section.label}` : "Chưa có bài"}
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </button>
                  </section>
                );
              })}
            </div>
          )}

          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <aside className="w-full shrink-0 rounded-3xl bg-white shadow-soft ring-1 ring-slate-100 lg:sticky lg:top-20 lg:w-72">
              <nav className="p-2" aria-label="Danh mục kiến thức">
                <button
                  type="button"
                  onClick={showOverview}
                  className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${
                    selectedId == null
                      ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  Tổng quan
                </button>
                {LEVEL_SECTIONS.map((section) => {
                  const items = articlesByLevel[section.key];
                  const isOpen = openSections[section.key];
                  return (
                    <div key={section.key} className="border-b border-slate-100 last:border-b-0">
                      <button
                        type="button"
                        onClick={() => toggleSection(section.key)}
                        className="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-3 text-left transition hover:bg-slate-50"
                        aria-expanded={isOpen}
                      >
                        <span className="flex items-center gap-2">
                          <span className={`badge ${section.badge}`}>{section.label}</span>
                          <span className="text-xs font-medium text-slate-400">{items.length} bài</span>
                        </span>
                        <svg
                          className={`h-4 w-4 shrink-0 text-slate-400 transition ${isOpen ? "rotate-180" : ""}`}
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth={2}
                          aria-hidden
                        >
                          <path d="M6 9l6 6 6-6" />
                        </svg>
                      </button>
                      {isOpen && items.length > 0 && (
                        <ul className="space-y-0.5 px-2 pb-2">
                          {items.map((article) => {
                            const active = article.id === selectedId;
                            const num = articleNumber(article.title_vi);
                            return (
                              <li key={article.id}>
                                <button
                                  type="button"
                                  onClick={() => selectArticle(article)}
                                  className={`w-full rounded-lg px-3 py-2.5 text-left text-sm leading-snug transition ${
                                    active
                                      ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                                      : "text-slate-700 hover:bg-slate-50"
                                  }`}
                                >
                                  <span className="block">
                                    {num && (
                                      <span className="mr-1.5 font-semibold text-slate-500">{num}</span>
                                    )}
                                    {numberedTitle(article.title_vi).replace(/^\d+\.\d+\s*[—–-]\s*/, "")}
                                  </span>
                                  {article.read_time_min != null && (
                                    <span className="mt-0.5 block text-[11px] font-normal text-slate-400">
                                      {article.read_time_min} phút đọc
                                    </span>
                                  )}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                      {isOpen && items.length === 0 && (
                        <p className="px-3 pb-3 text-xs text-slate-400">Chưa có bài ở mức này.</p>
                      )}
                    </div>
                  );
                })}
              </nav>
            </aside>

            <div className="min-w-0 flex-1 rounded-3xl bg-white p-5 shadow-soft ring-1 ring-slate-100 sm:p-7 lg:min-h-[28rem]">
              {selected ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className={`badge ${levelMeta(selected.level).badge}`}>
                      {levelMeta(selected.level).vi}
                    </span>
                    {selected.read_time_min != null && (
                      <span className="text-xs text-slate-400">{selected.read_time_min} phút đọc</span>
                    )}
                    <button
                      type="button"
                      onClick={showOverview}
                      className="ml-auto text-xs font-medium text-brand-600 hover:underline"
                    >
                      ← Tổng quan
                    </button>
                  </div>
                  <h2 className="mt-3 text-xl font-extrabold leading-snug tracking-tight sm:text-2xl">
                    {numberedTitle(selected.title_vi)}
                  </h2>
                  {articleLoading && !(selected.content_md && selected.content_md.length > 80) ? (
                    <p className="mt-5 text-sm text-slate-400">Đang tải bài…</p>
                  ) : (
                    <article
                      className="mt-5 text-[15px]"
                      dangerouslySetInnerHTML={{
                        __html: renderMarkdown((selected.content_md || "").replace(/^#\s+[^\n]+\n+/, "")),
                      }}
                    />
                  )}
                  <div className="mt-8 border-t border-slate-100 pt-5">
                    <p className="text-sm text-slate-500">Sẵn sàng tập? TAPTOT xếp lịch theo sức bạn.</p>
                    <Link
                      href="/batdau?moi=1"
                      className="mt-3 inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
                    >
                      Bắt đầu với TAPTOT
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </Link>
                  </div>
                </>
              ) : (
                <div>
                  <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Lời mở đầu</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-500">
                    Ba mức từ cơ bản đến nâng cao. Chọn thẻ phía trên hoặc mở mục bên trái để đọc.
                  </p>

                  <div className="mt-6 space-y-5">
                    {LEVEL_SECTIONS.map((section) => {
                      const items = articlesByLevel[section.key];
                      if (!items.length) return null;
                      return (
                        <section key={section.key}>
                          <div className="mb-2 flex items-center gap-2">
                            <span className={`badge ${section.badge}`}>{section.label}</span>
                            <span className="text-xs text-slate-400">{items.length} bài</span>
                          </div>
                          <ul className="grid gap-x-4 gap-y-1 sm:grid-cols-2">
                            {items.map((article) => {
                              const num = articleNumber(article.title_vi);
                              return (
                                <li key={article.id}>
                                  <button
                                    type="button"
                                    onClick={() => selectArticle(article)}
                                    className="w-full rounded-xl px-3 py-2 text-left text-[13px] leading-snug text-slate-700 transition hover:bg-brand-50 hover:text-brand-800"
                                  >
                                    {num && (
                                      <span className="mr-1.5 font-semibold text-slate-500">{num}</span>
                                    )}
                                    {numberedTitle(article.title_vi).replace(/^\d+\.\d+\s*[—–-]\s*/, "")}
                                  </button>
                                </li>
                              );
                            })}
                          </ul>
                        </section>
                      );
                    })}
                  </div>

                  <div className="mt-6 border-t border-slate-100 pt-5">
                    <Link
                      href="/batdau?moi=1"
                      className="inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
                    >
                      Bắt đầu với TAPTOT
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </Link>
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
