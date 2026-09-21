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
  },
  {
    key: "trung-cap" as const,
    label: "Trung cấp",
    badge: "badge-mid",
  },
  {
    key: "nang-cao" as const,
    label: "Nâng cao",
    badge: "badge-hard",
  },
];

const ADVANCED_PLACEHOLDER = "TAPTOT đang trao đổi với chuyên gia để chuẩn bị nội dung.";

const ADVANCED_TOPICS = [
  {
    key: "gym",
    label: "Gym",
    areas: ["Chương trình tập", "Kỹ thuật compound", "Quá tải và tiến bộ"],
  },
  {
    key: "calisthenics",
    label: "Calisthenics",
    areas: ["Lộ trình kỹ năng", "Sức mạnh tự trọng", "Handstand và kéo"],
  },
  {
    key: "the-thao",
    label: "Thể thao",
    areas: ["Sức mạnh chuyên môn", "Phòng chấn thương", "Chu kỳ mùa giải"],
  },
  {
    key: "chay-bo",
    label: "Chạy bộ",
    areas: ["Tăng thể lực", "Khối lượng và tốc độ", "Phục hồi"],
  },
  {
    key: "yoga",
    label: "Yoga",
    areas: ["Linh hoạt", "Sức bền", "Hơi thở và phục hồi"],
  },
  {
    key: "pilates",
    label: "Pilates",
    areas: ["Core", "Tư thế", "Kiểm soát hơi thở"],
  },
  {
    key: "dance",
    label: "Dance",
    areas: ["Cardio", "Nhịp điệu", "Sức bền"],
  },
  {
    key: "vo-thuat",
    label: "Võ thuật",
    areas: ["Kỹ thuật", "Thể lực", "Phản xạ"],
  },
] as const;

type AdvancedTopicKey = (typeof ADVANCED_TOPICS)[number]["key"];

function BackOverviewButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-800 shadow-soft transition hover:bg-brand-100"
    >
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      Tổng quan
    </button>
  );
}

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

export default function KnowledgeBase() {
  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [articleLoading, setArticleLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedTopicKey, setSelectedTopicKey] = useState<AdvancedTopicKey | null>(null);
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
      const bucket = levelBucket(article.level);
      if (bucket === "nang-cao") continue;
      map[bucket].push(article);
    }
    for (const key of Object.keys(map) as (typeof LEVEL_SECTIONS)[number]["key"][]) {
      map[key].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0) || a.id - b.id);
    }
    return map;
  }, [articles]);

  const selected = useMemo(
    () => articles.find((a) => a.id === selectedId && levelBucket(a.level) !== "nang-cao") ?? null,
    [articles, selectedId],
  );
  const selectedTopic = useMemo(
    () => ADVANCED_TOPICS.find((t) => t.key === selectedTopicKey) ?? null,
    [selectedTopicKey],
  );
  const showingOverview = selectedId == null && selectedTopicKey == null;

  function toggleSection(key: string) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function selectArticle(article: KnowledgeArticle) {
    if (levelBucket(article.level) === "nang-cao") return;
    setSelectedTopicKey(null);
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
    const match = articles.find((a) => a.slug === slug && levelBucket(a.level) !== "nang-cao");
    deepLinkHandled.current = true;
    if (match) selectArticle(match);
  }, [loading, articles]);

  function showOverview() {
    setSelectedId(null);
    setSelectedTopicKey(null);
  }

  function selectAdvancedTopic(key: AdvancedTopicKey) {
    setSelectedId(null);
    setSelectedTopicKey(key);
    setOpenSections((prev) => ({ ...prev, "nang-cao": true }));
  }

  return (
    <div className="pb-4">
      <div className="mb-5">
        <h1 className="type-display">Kho kiến thức</h1>
      </div>

      {error && (
        <div className="rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-600 ring-1 ring-rose-100">
          Lỗi tải dữ liệu: {error}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[18rem_1fr]">
          <div className="h-80 animate-pulse rounded-3xl bg-white shadow-soft" />
          <div className="min-h-80 animate-pulse rounded-3xl bg-white shadow-soft" />
        </div>
      ) : articles.length === 0 ? (
        <div className="rounded-3xl bg-white py-16 text-center text-slate-400 shadow-soft ring-1 ring-slate-100">
          <p className="font-medium">Chưa có bài viết</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[18rem_1fr]">
            <aside className="w-full rounded-3xl bg-white shadow-soft ring-1 ring-slate-100">
              <nav className="p-2" aria-label="Danh mục kiến thức">
                <button
                  type="button"
                  onClick={showOverview}
                  className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${
                    showingOverview
                      ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                      : "text-slate-700 hover:bg-slate-50"
                  }`}
                >
                  Tổng quan
                </button>
                {LEVEL_SECTIONS.map((section) => {
                  const items = articlesByLevel[section.key];
                  const isOpen = openSections[section.key];
                  const isAdvanced = section.key === "nang-cao";
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
                          <span className="text-xs font-medium text-slate-400">
                            {isAdvanced ? `${ADVANCED_TOPICS.length} mục` : `${items.length} bài`}
                          </span>
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
                      {isOpen && isAdvanced && (
                        <ul className="space-y-0.5 px-2 pb-2">
                          {ADVANCED_TOPICS.map((topic) => {
                            const active = topic.key === selectedTopicKey;
                            return (
                              <li key={topic.key}>
                                <button
                                  type="button"
                                  onClick={() => selectAdvancedTopic(topic.key)}
                                  className={`w-full rounded-lg px-3 py-2.5 text-left text-sm leading-snug transition ${
                                    active
                                      ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                                      : "text-slate-700 hover:bg-slate-50"
                                  }`}
                                >
                                  {topic.label}
                                </button>
                              </li>
                            );
                          })}
                        </ul>
                      )}
                      {isOpen && !isAdvanced && items.length > 0 && (
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
                      {isOpen && !isAdvanced && items.length === 0 && (
                        <p className="px-3 pb-3 text-xs text-slate-400">Chưa có bài ở mức này.</p>
                      )}
                    </div>
                  );
                })}
              </nav>
            </aside>

            <div className="min-w-0 flex-1 rounded-3xl bg-white p-5 shadow-soft ring-1 ring-slate-100 sm:p-7">
              {selected ? (
                <>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className={`badge ${levelMeta(selected.level).badge}`}>
                      {levelMeta(selected.level).vi}
                    </span>
                    {selected.read_time_min != null && (
                      <span className="text-xs text-slate-400">{selected.read_time_min} phút đọc</span>
                    )}
                    <div className="ml-auto">
                      <BackOverviewButton onClick={showOverview} />
                    </div>
                  </div>
                  <h2 className="mt-4 type-title">
                    {numberedTitle(selected.title_vi)}
                  </h2>
                  {articleLoading && !(selected.content_md && selected.content_md.length > 80) ? (
                    <p className="mt-5 text-sm text-slate-400">Đang tải bài…</p>
                  ) : (
                    <article
                      className="type-body mt-5 text-[15px]"
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
              ) : selectedTopic ? (
                <div>
                  <div className="flex flex-wrap items-center gap-3">
                    <span className="badge badge-hard">Nâng cao</span>
                    <div className="ml-auto">
                      <BackOverviewButton onClick={showOverview} />
                    </div>
                  </div>
                  <h2 className="mt-4 type-title">{selectedTopic.label}</h2>
                  <div className="mt-5 grid gap-3 sm:grid-cols-2">
                    {selectedTopic.areas.map((area) => (
                      <section key={area} className="rounded-2xl bg-slate-50 p-4 ring-1 ring-slate-100">
                        <h3 className="font-semibold text-slate-900">{area}</h3>
                        <p className="mt-2 text-sm leading-relaxed text-slate-500">{ADVANCED_PLACEHOLDER}</p>
                      </section>
                    ))}
                  </div>
                </div>
              ) : (
                <div>
                  <h2 className="type-title">Lời mở đầu</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-500">
                    Mở mục bên trái để đọc theo mức cơ bản, trung cấp, hoặc chọn mục chuyên sâu ở Nâng cao.
                  </p>

                  <div className="mt-6 space-y-5">
                    {LEVEL_SECTIONS.filter((section) => section.key !== "nang-cao").map((section) => {
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
