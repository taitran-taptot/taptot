"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { cookPostHref, COOK_HREF, FOOD_AI_REFERENCE_NOTE } from "@/lib/foodRoutes";
import { mediaUrl, viNum } from "@/lib/labels";
import type { CookingPost } from "@/lib/types";
import FoodBrowseTabs from "./FoodBrowseTabs";
import BrandHero from "@/components/BrandHero";
import { brandRichText } from "@/components/brandRichText";

const PAGE_SIZE = 9;

const GROUPS: { slug: string; nameVi: string }[] = [
  { slug: "mon-com-gia-dinh", nameVi: "Món Cơm Gia Đình" },
  { slug: "dac-san-vung-mien", nameVi: "Đặc sản vùng miền" },
  { slug: "mon-nuoc-soi", nameVi: "Món Nước & Sợi" },
  { slug: "banh-mi-mon-cuon", nameVi: "Bánh Mì & Món Cuốn" },
];

function postDetailHref(basePath: string, slug: string): string {
  if (basePath === COOK_HREF || basePath === "/cach-nau") return cookPostHref(slug);
  return `${basePath}?mon=${encodeURIComponent(slug)}`;
}

export default function CookingPosts({ basePath = "/cach-nau" }: { basePath?: string }) {
  const [items, setItems] = useState<CookingPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [group, setGroup] = useState("");
  const [page, setPage] = useState(1);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    cookingPostsApi
      .listPublic(1, 100)
      .then((d) => setItems(d.items || []))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(
    () => (group ? items.filter((p) => p.group_slug === group) : items),
    [items, group],
  );

  const pageCount = Math.max(1, Math.ceil(visible.length / PAGE_SIZE));
  const paged = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return visible.slice(start, start + PAGE_SIZE);
  }, [visible, page]);

  useEffect(() => {
    setPage(1);
  }, [group]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  function goPage(next: number) {
    setPage(next);
    listRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <section>
      <BrandHero title="Cách nấu món ăn ngon" className="mb-6">
        <p className="mt-4 text-sm leading-relaxed text-white/85">{brandRichText(FOOD_AI_REFERENCE_NOTE)}</p>
      </BrandHero>

      <FoodBrowseTabs />

      <div className="mb-4 flex flex-wrap gap-2">
        <button
          type="button"
          onClick={() => setGroup("")}
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            group === "" ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600"
          }`}
        >
          Tất cả
        </button>
        {GROUPS.map((g) => (
          <button
            key={g.slug}
            type="button"
            onClick={() => setGroup(g.slug)}
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              group === g.slug ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {g.nameVi}
          </button>
        ))}
      </div>

      {error && <div className="py-12 text-center text-rose-500">Lỗi tải dữ liệu: {error}</div>}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: PAGE_SIZE }).map((_, i) => (
            <div key={i} className="h-56 animate-pulse rounded-2xl bg-white shadow-soft" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="py-16 text-center text-slate-400">
          <p className="font-medium">Chưa có bài viết. Quay lại sau nhé.</p>
        </div>
      ) : (
        <div ref={listRef}>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {paged.map((p) => {
            const cover = mediaUrl(p.cover_image_url);
            const grams = p.yield_grams ? `~${Math.round(p.yield_grams)} g` : null;
            const kcal =
              p.serving_calories != null
                ? `~${viNum(p.serving_calories)} calo/suất`
                : p.dish_calories != null
                  ? `~${viNum(p.dish_calories)} calo/suất`
                  : null;
            return (
              <Link
                key={p.id}
                href={postDetailHref(basePath, p.slug)}
                className="card-media-zoom group flex flex-col overflow-hidden rounded-2xl bg-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="h-40 bg-gradient-to-br from-accent-100 to-accent-200">
                  {cover ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={cover} alt={p.title_vi} className="h-full w-full object-cover" />
                  ) : (
                    <div className="grid h-full place-items-center text-4xl">🍳</div>
                  )}
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <h2 className="font-bold leading-snug group-hover:text-brand-700">{p.title_vi}</h2>
                  {(p.servings || grams || kcal) && (
                    <p className="mt-1 text-xs font-semibold text-brand-700">
                      {[p.servings ? `${p.servings} người` : null, grams, kcal].filter(Boolean).join(" · ")}
                    </p>
                  )}
                  {p.excerpt && (
                    <p className="mt-2 line-clamp-2 flex-1 text-sm text-slate-500">{p.excerpt}</p>
                  )}
                  <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand-600">
                    Đọc bài
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
        <CookPager page={page} pages={pageCount} total={visible.length} onPage={goPage} />
        </div>
      )}
    </section>
  );
}

function pageNumbers(page: number, pages: number): (number | "…")[] {
  if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
  const nums: (number | "…")[] = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(pages - 1, page + 1);
  if (start > 2) nums.push("…");
  for (let i = start; i <= end; i++) nums.push(i);
  if (end < pages - 1) nums.push("…");
  nums.push(pages);
  return nums;
}

function CookPager({
  page,
  pages,
  total,
  onPage,
}: {
  page: number;
  pages: number;
  total: number;
  onPage: (n: number) => void;
}) {
  if (pages <= 1) return null;
  const from = (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);
  return (
    <nav className="mt-6 flex flex-wrap items-center justify-between gap-3" aria-label="Phân trang">
      <p className="text-sm text-slate-500">
        {from.toLocaleString("vi-VN")}–{to.toLocaleString("vi-VN")} / {total.toLocaleString("vi-VN")} bài
      </p>
      <div className="flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPage(page - 1)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Trước
        </button>
        {pageNumbers(page, pages).map((n, i) =>
          n === "…" ? (
            <span key={`e-${i}`} className="px-1 text-sm text-slate-400">
              …
            </span>
          ) : (
            <button
              key={n}
              type="button"
              onClick={() => onPage(n)}
              aria-current={n === page ? "page" : undefined}
              className={`min-w-8 rounded-xl px-2.5 py-1.5 text-sm font-semibold transition ${
                n === page
                  ? "bg-brand-500 text-white shadow-soft"
                  : "border border-slate-200 bg-white text-slate-700 hover:border-brand-400 hover:text-brand-600"
              }`}
            >
              {n}
            </button>
          ),
        )}
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPage(page + 1)}
          className="rounded-xl border border-slate-200 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-brand-400 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Sau
        </button>
      </div>
    </nav>
  );
}
