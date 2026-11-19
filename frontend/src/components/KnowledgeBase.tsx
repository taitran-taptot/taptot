"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState, type MouseEvent, type ReactNode } from "react";
import { api } from "@/lib/api";
import { renderMarkdown } from "@/lib/markdown";
import type { KnowledgeArticle } from "@/lib/types";
import { knowledgeHref, knowledgeSlugFromPathname } from "@/lib/phaseKnowledge";
import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";
import {
  KNOWLEDGE_PATHS,
  articleTitleWithoutCode,
  knowledgeReadBadge,
  pathForSlug,
  type KnowledgePath,
} from "@/lib/knowledgePath";
import BrandHero from "@/components/BrandHero";
import { brandRichText } from "@/components/brandRichText";

function goKnowledgeOverview(
  event: MouseEvent<HTMLAnchorElement>,
  router: ReturnType<typeof useRouter>,
) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
    return;
  }
  event.preventDefault();
  router.push("/kien-thuc");
}

function goBack(
  event: MouseEvent<HTMLAnchorElement>,
  router: ReturnType<typeof useRouter>,
) {
  if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) {
    return;
  }
  event.preventDefault();
  if (window.history.length > 1) {
    router.back();
    return;
  }
  router.push("/kien-thuc");
}

function BackLink() {
  const router = useRouter();
  return (
    <Link
      href="/kien-thuc"
      className="inline-flex items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-800 shadow-soft transition hover:bg-brand-100"
      onClick={(event) => goBack(event, router)}
    >
      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      Quay lại
    </Link>
  );
}

function PathIcon({ pathKey }: { pathKey: string }) {
  const common = "h-9 w-9";
  if (pathKey === "lich-tap") {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <rect x="4" y="5" width="16" height="15" rx="2" />
        <path d="M8 3.5v3M16 3.5v3M4 9.5h16M8 13.5h3M8 16.5h6" />
      </svg>
    );
  }
  if (pathKey === "dinh-duong") {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
      </svg>
    );
  }
  if (pathKey === "toi-uu") {
    return (
      <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
        <path d="M3 17l6-6 4 4 8-8" />
        <path d="M15 7h6v6" />
      </svg>
    );
  }
  return (
    <svg className={common} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 6.2A8.5 8.5 0 0 0 6.2 4C5.2 4 4.2 4.2 3.2 4.5v13.2A8.4 8.4 0 0 1 6.2 17 8.5 8.5 0 0 1 12 19.2" />
      <path d="M12 6.2A8.5 8.5 0 0 1 17.8 4c1 0 2 .2 3 .5v13.2A8.4 8.4 0 0 0 17.8 17 8.5 8.5 0 0 0 12 19.2" />
      <path d="M12 6.2v13" />
    </svg>
  );
}

function articleLabel(title: string) {
  return articleTitleWithoutCode(title);
}

function articlesForSlugs(articles: KnowledgeArticle[], slugs: string[]) {
  const bySlug = new Map(articles.map((article) => [article.slug, article]));
  return slugs.flatMap((slug) => {
    const article = bySlug.get(slug);
    return article ? [article] : [];
  });
}

function ArticleLink({
  article,
  className,
  showChevron = false,
}: {
  article: KnowledgeArticle;
  className: string;
  showChevron?: boolean;
}) {
  return (
    <Link href={knowledgeHref(article.slug)} className={className}>
      <span className="min-w-0 flex-1">
        <span className="block">{articleLabel(article.title_vi)}</span>
        {article.read_time_min != null && (
          <span className="mt-0.5 block text-[11px] font-normal text-slate-400">
            {article.read_time_min} phút đọc
          </span>
        )}
      </span>
      {showChevron && (
        <svg
          className="h-5 w-5 shrink-0 text-slate-400 lg:hidden"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden
        >
          <path d="M9 6l6 6-6 6" />
        </svg>
      )}
    </Link>
  );
}

function PathRows() {
  return (
    <ul className="mt-4 grid grid-cols-1 gap-3 lg:grid-cols-4">
      {KNOWLEDGE_PATHS.map((path) => (
        <li key={path.key} className="min-w-0">
          <Link
            href={`/kien-thuc?nhom=${path.key}`}
            className="flex h-full items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-4 text-left shadow-soft transition hover:border-brand-200 hover:bg-brand-50 lg:flex-col lg:items-center lg:border-0 lg:bg-slate-50 lg:text-center lg:shadow-none lg:ring-1 lg:ring-slate-100 lg:hover:bg-brand-50 lg:hover:ring-brand-100"
          >
            <span className="grid h-12 w-12 shrink-0 place-items-center rounded-full bg-brand-50 text-brand-700 lg:h-16 lg:w-16 lg:bg-white lg:shadow-soft">
              <PathIcon pathKey={path.key} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block font-bold text-slate-900">{path.title}</span>
              <span className="mt-1 block text-sm leading-snug text-slate-500">{path.subtitle}</span>
            </span>
            <svg
              className="h-5 w-5 shrink-0 text-slate-400 lg:hidden"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              aria-hidden
            >
              <path d="M9 6l6 6-6 6" />
            </svg>
          </Link>
        </li>
      ))}
    </ul>
  );
}

export default function KnowledgeBase({ initialSlug = "" }: { initialSlug?: string }) {
  const pathname = usePathname() || "";
  const router = useRouter();
  const searchParams = useSearchParams();
  const urlSlug = canonicalizeKnowledgeSlug(
    knowledgeSlugFromPathname(pathname) ||
      (searchParams.get("bai") || searchParams.get("slug") || "").trim() ||
      initialSlug.trim(),
  );
  const pathParam = (searchParams.get("nhom") || "").trim();

  const [articles, setArticles] = useState<KnowledgeArticle[]>([]);
  const [loading, setLoading] = useState(true);
  const [articleLoading, setArticleLoading] = useState(false);
  const [error, setError] = useState("");
  const [openSections, setOpenSections] = useState<Record<string, boolean>>({});

  useEffect(() => {
    api
      .knowledgeArticles()
      .then((a) => setArticles((a.items || []).filter((x) => x.is_published !== false)))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const selected = useMemo(
    () => (urlSlug ? (articles.find((a) => a.slug === urlSlug) ?? null) : null),
    [articles, urlSlug],
  );
  const selectedPath = useMemo(() => {
    if (selected) return pathForSlug(selected.slug);
    return KNOWLEDGE_PATHS.find((path) => path.key === pathParam) ?? null;
  }, [pathParam, selected]);

  useEffect(() => {
    if (!selectedPath) return;
    setOpenSections((prev) => ({ ...prev, [selectedPath.key]: true }));
  }, [selectedPath]);

  useEffect(() => {
    if (!selected) return;
    if (selected.content_md && selected.content_md.length > 80) return;
    const id = selected.id;
    let cancelled = false;
    setArticleLoading(true);
    api
      .knowledgeArticle(id)
      .then((full) => {
        if (cancelled) return;
        setArticles((prev) => prev.map((row) => (row.id === full.id ? { ...row, ...full } : row)));
      })
      .catch((e) => {
        if (!cancelled) setError((e as Error).message);
      })
      .finally(() => {
        if (!cancelled) setArticleLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected]);

  function toggleSection(key: string) {
    setOpenSections((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const unknownSlug = Boolean(urlSlug) && !loading && !selected;
  const showingOverview = !urlSlug && !selectedPath;
  const hideAsideOnMobile = Boolean(selected || selectedPath || unknownSlug);

  const articleLinkClass = (active: boolean) =>
    `block w-full rounded-lg px-3 py-2.5 text-left text-sm leading-snug transition ${
      active
        ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
        : "text-slate-700 hover:bg-slate-50"
    }`;

  let main: ReactNode;
  if (unknownSlug) {
    main = (
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <div className="ml-auto">
            <BackLink />
          </div>
        </div>
        <h2 className="mt-4 type-title">Không tìm thấy bài viết</h2>
        <p className="mt-3 text-sm leading-relaxed text-slate-500">
          Bài này không tồn tại hoặc đã bị gỡ. Quay lại tổng quan để chọn bài khác.
        </p>
      </div>
    );
  } else if (selected) {
    const path = pathForSlug(selected.slug);
    main = (
      <>
        <div className="flex flex-wrap items-center gap-3">
          {path && (
            <span className={`badge ${knowledgeReadBadge(path.readWhen)}`}>{path.readLabel}</span>
          )}
          {selected.read_time_min != null && (
            <span className="text-xs text-slate-400">{selected.read_time_min} phút đọc</span>
          )}
          <div className="ml-auto">
            <BackLink />
          </div>
        </div>
        <h2 className="mt-4 type-title">{articleLabel(selected.title_vi)}</h2>
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
          <p className="text-sm text-slate-500">
            Sẵn sàng tập? {brandRichText("TAPTOT")} xếp lịch theo sức bạn.
          </p>
          <Link
            href="/batdau?moi=1"
            className="mt-3 inline-flex items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
          >
            Bắt đầu
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
              <path d="M5 12h14M13 6l6 6-6 6" />
            </svg>
          </Link>
        </div>
      </>
    );
  } else if (selectedPath) {
    main = (
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <span className={`badge ${knowledgeReadBadge(selectedPath.readWhen)}`}>
            {selectedPath.readLabel}
          </span>
          <div className="ml-auto">
            <BackLink />
          </div>
        </div>
        <h2 className="mt-4 type-title">{selectedPath.title}</h2>
        <p className="mt-2 text-sm leading-relaxed text-slate-500">{selectedPath.subtitle}</p>
        <ul className="mt-6 space-y-2 lg:space-y-0.5">
          {selectedPath.stages.flatMap((stage) =>
            articlesForSlugs(articles, stage.slugs).map((article) => (
              <li key={article.id}>
                <ArticleLink
                  article={article}
                  showChevron
                  className="flex w-full items-center gap-3 rounded-2xl border border-slate-200 bg-white px-4 py-3.5 text-left text-sm font-semibold leading-snug text-slate-800 shadow-soft transition hover:border-brand-200 hover:bg-brand-50 lg:block lg:rounded-xl lg:border-0 lg:bg-transparent lg:px-3 lg:py-2.5 lg:font-normal lg:text-slate-700 lg:shadow-none lg:hover:bg-brand-50 lg:hover:text-brand-800"
                />
              </li>
            )),
          )}
        </ul>
      </div>
    );
  } else {
    main = (
      <div>
        <h2 className="type-title text-center">Nhóm kiến thức</h2>
        <PathRows />
      </div>
    );
  }

  return (
    <div className="pb-4">
      <BrandHero title="Kho kiến thức" className="mb-5" wide>
        <p className="mt-4 text-sm leading-relaxed text-white/85 lg:whitespace-nowrap lg:text-[13px]">
          {brandRichText(
            "Mọi thông tin, bài viết trên kho kiến thức của TAPTOT chỉ nhằm mục đích chia sẻ kiến thức, tham khảo và nâng cao sức khỏe cộng đồng.",
          )}
        </p>
      </BrandHero>

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
        <div
          className={
            showingOverview
              ? "grid grid-cols-1"
              : "grid grid-cols-1 items-start gap-5 lg:grid-cols-[18rem_1fr]"
          }
        >
          <aside
            className={`w-full rounded-3xl bg-white shadow-soft ring-1 ring-slate-100 ${
              showingOverview ? "hidden" : hideAsideOnMobile ? "hidden lg:block" : ""
            }`}
          >
            <nav className="p-2" aria-label="Danh mục kiến thức">
              <Link
                href="/kien-thuc"
                className="mb-1 block w-full rounded-xl px-3 py-2.5 text-left text-sm text-slate-700 transition hover:bg-slate-50"
                onClick={(event) => goKnowledgeOverview(event, router)}
              >
                Tổng quan
              </Link>
              {KNOWLEDGE_PATHS.map((path) => (
                <PathSection
                  key={path.key}
                  path={path}
                  articles={articles}
                  open={Boolean(openSections[path.key])}
                  urlSlug={urlSlug}
                  onToggle={() => toggleSection(path.key)}
                  articleLinkClass={articleLinkClass}
                />
              ))}
            </nav>
          </aside>

          <div className="min-w-0 flex-1 rounded-3xl bg-white p-5 shadow-soft ring-1 ring-slate-100 sm:p-7">
            {main}
          </div>
        </div>
      )}
    </div>
  );
}

function PathSection({
  path,
  articles,
  open,
  urlSlug,
  onToggle,
  articleLinkClass,
}: {
  path: KnowledgePath;
  articles: KnowledgeArticle[];
  open: boolean;
  urlSlug: string;
  onToggle: () => void;
  articleLinkClass: (active: boolean) => string;
}) {
  const count = path.stages.reduce((sum, stage) => sum + articlesForSlugs(articles, stage.slugs).length, 0);
  return (
    <div className="border-b border-slate-100 last:border-b-0">
      <button
        type="button"
        onClick={onToggle}
        className="flex w-full items-center justify-between gap-2 rounded-xl px-3 py-3 text-left transition hover:bg-slate-50"
        aria-expanded={open}
      >
        <span className="min-w-0">
          <span className="block text-sm font-semibold text-slate-800">
            {path.title}
          </span>
          <span className="block text-xs font-medium text-slate-400">{count} bài</span>
        </span>
        <svg
          className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? "rotate-180" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          aria-hidden
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>
      {open && (
        <ul className="space-y-0.5 px-2 pb-3">
          {path.stages.flatMap((stage) =>
            articlesForSlugs(articles, stage.slugs).map((article) => (
              <li key={article.id}>
                <ArticleLink
                  article={article}
                  className={articleLinkClass(article.slug === urlSlug)}
                />
              </li>
            )),
          )}
        </ul>
      )}
    </div>
  );
}
