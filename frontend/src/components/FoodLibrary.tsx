"use client";

import { useEffect, useMemo, useRef, useState, Suspense } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { FOODS_HREF, cookPostHref, FOOD_AI_REFERENCE_NOTE } from "@/lib/foodRoutes";
import BrandHero from "@/components/BrandHero";
import { brandRichText } from "@/components/brandRichText";
import { api } from "@/lib/api";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import {
  collectSubgroups,
  foodDisplayName,
  foodKcalLine,
  foodPer100g,
  foodRoleLabel,
  foodServingNutrients,
  foodSubgroup,
  isHiddenFoodCategorySlug,
  servingIs100g,
  type FoodNutrients,
} from "@/lib/foodDisplay";
import { mediaUrl, viNum } from "@/lib/labels";
import type { CookingPost, Food, FoodCategory } from "@/lib/types";
import FoodAisleChips from "./FoodAisleChips";
import FoodAmountConverter from "./FoodAmountConverter";
import FoodBrowseTabs from "./FoodBrowseTabs";
import MacroBar from "./MacroBar";
import Modal from "./Modal";

const FOOD_PAGE_SIZE = 24;
const COOKED_AISLE_SLUGS = new Set([
  "com-trang",
  "bun-tuoi",
  "banh-pho-tuoi",
  "rau-muong-luoc",
  "bap-ngot-luoc",
]);

function isAisleIngredient(food: Food): boolean {
  if (!food.image_url) return false;
  if ((food.food_kind || "ingredient") === "dish") return true;
  const cooked = (food.prep_state || "").toLowerCase() === "cooked";
  if (cooked && !COOKED_AISLE_SLUGS.has(food.slug)) return false;
  return true;
}

type AisleTheme = {
  tile: string;
  icon: string;
};

const AISLE: Record<string, AisleTheme> = {
  "rau-cu-qua": {
    tile: "from-brand-100 to-emerald-50",
    icon: "text-brand-800",
  },
  "thit-gia-cam-noi-tang": {
    tile: "from-rose-100 to-orange-100",
    icon: "text-rose-700",
  },
  "ca-thuy-hai-san": {
    tile: "from-sky-100 to-cyan-50",
    icon: "text-sky-800",
  },
  "trung-whey": {
    tile: "from-orange-50 to-amber-100",
    icon: "text-amber-900",
  },
  "ngu-coc-hat": {
    tile: "from-amber-50 to-lime-50",
    icon: "text-amber-800",
  },
  "mon-an-truyen-thong": {
    tile: "from-amber-100 to-yellow-50",
    icon: "text-amber-800",
  },
  "gia-vi-mam-dau": {
    tile: "from-amber-50 to-orange-50",
    icon: "text-amber-800",
  },
};

function aisleTheme(slug: string): AisleTheme {
  return (
    AISLE[slug] || {
      tile: "from-slate-100 to-slate-50",
      icon: "text-slate-600",
    }
  );
}

function AisleIcon({ slug, className }: { slug: string; className?: string }) {
  const cls = `h-8 w-8 ${className || ""}`;
  if (slug === "thit-gia-cam-noi-tang") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M4 14c2-6 8-8 14-5 1 4-1 8-5 9-4 1-8-1-9-4Z" />
        <path d="M8 12h.01M12 10h.01" />
      </svg>
    );
  }
  if (slug === "rau-cu-qua") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M12 21c4-2 7-7 7-11a7 7 0 1 0-14 0c0 4 3 9 7 11Z" />
        <path d="M12 10V4" />
      </svg>
    );
  }
  if (slug === "ca-thuy-hai-san") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M3 12s3-5 9-5 9 5 9 5-3 5-9 5-9-5-9-5Z" />
        <path d="M14.5 10.5h.01" />
        <path d="M3 12c2 1 3 3 3 5" />
      </svg>
    );
  }
  if (slug === "trung-whey") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M12 4c3.5 0 6 4.2 6 8.5S15.5 20 12 20 6 16.8 6 12.5 8.5 4 12 4Z" />
      </svg>
    );
  }
  if (slug === "ngu-coc-hat") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M12 20c3.5-1.2 6-4.5 6-8 0-4-2.5-7-6-9-3.5 2-6 5-6 9 0 3.5 2.5 6.8 6 8Z" />
        <path d="M12 11c1.5-2 3-3 5-3" />
      </svg>
    );
  }
  if (slug === "mon-an-truyen-thong") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M4 11h16l-1.2 7.2A2 2 0 0 1 16.8 20H7.2a2 2 0 0 1-2-1.8L4 11Z" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </svg>
    );
  }
  return (
    <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
      <rect x="5" y="7" width="14" height="12" rx="1.5" />
      <path d="M5 11h14M12 7v12" />
    </svg>
  );
}

function FoodVisual({
  food,
  slug,
  className = "h-36",
  eager = false,
}: {
  food?: Food | null;
  slug: string;
  className?: string;
  eager?: boolean;
}) {
  const theme = aisleTheme(slug);
  const src = mediaUrl(food?.image_url);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const loadedSrc = useRef<string | null>(null);
  const showPhoto = Boolean(src) && failedSrc !== src;
  return (
    <div className={`relative overflow-hidden bg-gradient-to-br ${theme.tile} ${className}`}>
      {src ? (
        // Keep <img> mounted so a re-render cannot abort the request and hide the photo.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          loading={eager ? "eager" : "lazy"}
          decoding="async"
          className={`h-full w-full object-cover ${showPhoto ? "" : "invisible"}`}
          onLoad={() => {
            loadedSrc.current = src;
            setFailedSrc((prev) => (prev === src ? null : prev));
          }}
          onError={() => {
            if (loadedSrc.current === src) return;
            setFailedSrc(src);
          }}
        />
      ) : null}
      {!showPhoto && (
        <div className={`absolute inset-0 grid place-items-center ${theme.icon}`}>
          <AisleIcon slug={slug} className="h-10 w-10" />
        </div>
      )}
    </div>
  );
}

function foodCardMeta(food: Food): string {
  const role = foodRoleLabel(food);
  const per100 = foodPer100g(food);
  const kcalPart = servingIs100g(food)
    ? `${viNum(per100?.calories ?? food.calories)} calo / 100g`
    : foodKcalLine(food);
  return [role, kcalPart].filter(Boolean).join(" · ");
}

function sortAisleFoods(items: Food[]): Food[] {
  return [...items].sort((a, b) => {
    const aPhoto = a.image_url ? 1 : 0;
    const bPhoto = b.image_url ? 1 : 0;
    if (aPhoto !== bPhoto) return bPhoto - aPhoto;
    if (a.is_common !== b.is_common) return a.is_common ? -1 : 1;
    return foodDisplayName(a.name_vi).localeCompare(foodDisplayName(b.name_vi), "vi");
  });
}

async function loadAllFoods(signal?: AbortSignal): Promise<Food[]> {
  const pageSize = 100;
  const first = await api.searchFoods({ page: 1, page_size: pageSize });
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  const items = [...first.items];
  if (first.pages <= 1) return items;
  const rest = await Promise.all(
    Array.from({ length: first.pages - 1 }, (_, i) =>
      api.searchFoods({ page: i + 2, page_size: pageSize }),
    ),
  );
  if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
  for (const data of rest) items.push(...data.items);
  return items;
}

function matchesQuery(food: Food, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const nameVi = (food.name_vi || "").toLowerCase();
  const display = foodDisplayName(food.name_vi).toLowerCase();
  const nameEn = (food.name_en || "").toLowerCase();
  return nameVi.includes(q) || display.includes(q) || nameEn.includes(q);
}

export default function FoodLibrary() {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setReady(true);
  }, []);
  if (!ready) {
    return <div className="py-16 text-center text-sm text-slate-400">Đang tải…</div>;
  }
  return (
    <Suspense fallback={<div className="py-16 text-center text-sm text-slate-400">Đang tải…</div>}>
      <FoodLibraryInner />
    </Suspense>
  );
}

function FoodLibraryInner() {
  const pathname = usePathname() || FOODS_HREF;
  const router = useRouter();
  const searchParams = useSearchParams();
  const [categories, setCategories] = useState<FoodCategory[]>([]);
  const [foods, setFoods] = useState<Food[]>([]);
  const [remoteHits, setRemoteHits] = useState<Food[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [selectedSubgroup, setSelectedSubgroup] = useState("");
  const [detailOpen, setDetailOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const slug = (searchParams.get("slug") || "").trim();
    if (!slug || foods.length === 0) return;
    const hit = foods.find((food) => food.slug === slug);
    if (!hit) return;
    setSelectedId(hit.id);
    setDetailOpen(true);
    setSelectedCategoryId(null);
    setQ("");
  }, [searchParams, foods]);

  useEffect(() => {
    const ac = new AbortController();
    setLoading(true);
    setError("");
    Promise.all([api.foodCategories(), loadAllFoods(ac.signal)])
      .then(([catRes, allFoods]) => {
        if (ac.signal.aborted) return;
        const sorted = [...catRes.items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        setCategories(sorted);
        setFoods(sortAisleFoods(allFoods));
      })
      .catch((e) => {
        if (ac.signal.aborted || (e as Error)?.name === "AbortError") return;
        setError((e as Error).message || "Không tải được kho thực phẩm.");
      })
      .finally(() => {
        if (!ac.signal.aborted) setLoading(false);
      });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const query = q.trim();
    if (query.length < 2) {
      setRemoteHits(null);
      return;
    }
    const ac = new AbortController();
    api
      .searchFoods({ page: 1, page_size: 100, q: query })
      .then((data) => {
        if (ac.signal.aborted) return;
        setRemoteHits(data.items);
      })
      .catch(() => {
        if (!ac.signal.aborted) setRemoteHits(null);
      });
    return () => ac.abort();
  }, [q]);

  useEffect(() => {
    if (q.trim()) {
      setSelectedId(null);
      setSelectedCategoryId(null);
      setSelectedSubgroup("");
    }
    setPage(1);
  }, [q]);

  useEffect(() => {
    setPage(1);
  }, [selectedCategoryId, selectedSubgroup]);

  const aisleCategories = useMemo(
    () => categories.filter((c) => !isHiddenFoodCategorySlug(c.slug)),
    [categories],
  );

  const ingredientFoods = useMemo(
    () => foods.filter(isAisleIngredient),
    [foods],
  );

  const filteredFoods = useMemo(() => {
    const source = q.trim().length >= 2 && remoteHits ? remoteHits : ingredientFoods;
    let list = source.filter(isAisleIngredient);
    if (!(q.trim().length >= 2 && remoteHits)) {
      list = list.filter((f) => matchesQuery(f, q));
    }
    if (selectedSubgroup) {
      list = list.filter((f) => foodSubgroup(f)?.slug === selectedSubgroup);
    }
    return list;
  }, [ingredientFoods, q, remoteHits, selectedSubgroup]);

  const foodsByCategory = useMemo(() => {
    const map = new Map<number, Food[]>();
    for (const cat of aisleCategories) map.set(cat.id, []);
    for (const food of filteredFoods) {
      if (food.category_id != null && map.has(food.category_id)) {
        map.get(food.category_id)!.push(food);
      }
    }
    for (const [id, items] of map) map.set(id, sortAisleFoods(items));
    return map;
  }, [aisleCategories, filteredFoods]);

  const aisleCounts = useMemo(() => {
    const counts: Record<number, number> = {};
    for (const cat of aisleCategories) counts[cat.id] = foodsByCategory.get(cat.id)?.length || 0;
    return counts;
  }, [aisleCategories, foodsByCategory]);

  const chipCategories = useMemo(
    () => (q.trim() ? aisleCategories.filter((c) => (aisleCounts[c.id] || 0) > 0) : aisleCategories),
    [q, aisleCategories, aisleCounts],
  );

  const selected = useMemo(
    () => foods.find((f) => f.id === selectedId) ?? null,
    [foods, selectedId],
  );

  const activeCategory = useMemo(
    () => aisleCategories.find((c) => c.id === selectedCategoryId) ?? null,
    [aisleCategories, selectedCategoryId],
  );

  const categoryFoods = useMemo(() => {
    if (selectedCategoryId == null) return [];
    return foodsByCategory.get(selectedCategoryId) || [];
  }, [foodsByCategory, selectedCategoryId]);

  const subgroupOptions = useMemo(() => collectSubgroups(categoryFoods), [categoryFoods]);

  const searching = Boolean(q.trim());

  const gridList = searching && selectedCategoryId == null ? filteredFoods : categoryFoods;
  const pageCount = Math.max(1, Math.ceil(gridList.length / FOOD_PAGE_SIZE));
  const pagedFoods = useMemo(() => {
    const start = (page - 1) * FOOD_PAGE_SIZE;
    return gridList.slice(start, start + FOOD_PAGE_SIZE);
  }, [gridList, page]);

  useEffect(() => {
    if (page > pageCount) setPage(pageCount);
  }, [page, pageCount]);

  function goPage(next: number) {
    setPage(next);
    panelRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const slugByCategoryId = useMemo(
    () => Object.fromEntries(categories.map((c) => [c.id, c.slug])),
    [categories],
  );

  function selectFood(food: Food) {
    setSelectedId(food.id);
    setDetailOpen(true);
    if (food.category_id != null && selectedCategoryId != null) {
      setSelectedCategoryId(food.category_id);
    }
  }

  function closeFoodDetail() {
    setDetailOpen(false);
    const slug = (searchParams.get("slug") || "").trim();
    if (slug) {
      router.replace(pathname);
    }
  }

  function selectCategory(id: number) {
    setSelectedCategoryId(id);
    setSelectedSubgroup("");
    setSelectedId(null);
    setDetailOpen(false);
  }

  function showOverview() {
    setSelectedId(null);
    setSelectedCategoryId(null);
    setSelectedSubgroup("");
    setDetailOpen(false);
  }

  function onChipSelect(next: number | "") {
    if (next === "") showOverview();
    else selectCategory(next);
  }

  return (
    <section>
      <BrandHero title="Kho thực phẩm Việt" className="mb-5">
        <p className="mt-4 text-sm leading-relaxed text-white/85">{brandRichText(FOOD_AI_REFERENCE_NOTE)}</p>
      </BrandHero>

      <FoodBrowseTabs />

      <div className="mb-4 rounded-2xl bg-white p-3 shadow-soft sm:p-4">
        <div className="relative">
          <svg
            className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-slate-400"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            aria-hidden
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-3.5-3.5" />
          </svg>
          <label className="sr-only" htmlFor="food-search">
            Tìm thực phẩm
          </label>
          <input
            id="food-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            type="search"
            placeholder="Tìm… (vd: ức gà, cơm trắng, chuối, phở)"
            className="field pl-10"
          />
        </div>
        <div className="lg:hidden">
          <FoodAisleChips
            categories={chipCategories}
            allCount={filteredFoods.length}
            counts={aisleCounts}
            selected={selectedCategoryId ?? ""}
            onSelect={onChipSelect}
          />
        </div>
        {selectedCategoryId != null && subgroupOptions.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setSelectedSubgroup("")}
              className={`chip ${selectedSubgroup === "" ? "chip-active" : ""}`}
            >
              Tất cả nhóm
            </button>
            {subgroupOptions.map((g) => (
              <button
                key={g.slug}
                type="button"
                onClick={() => setSelectedSubgroup(g.slug)}
                className={`chip ${selectedSubgroup === g.slug ? "chip-active" : ""}`}
              >
                {g.nameVi}
              </button>
            ))}
          </div>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-600">
          Lỗi tải dữ liệu: {error}
          {foods.length > 0 ? " (đang hiện dữ liệu đã tải trước đó)" : ""}
        </div>
      )}

      {loading ? (
        <div className="min-h-80 animate-pulse rounded-2xl bg-white shadow-soft" />
      ) : foods.length === 0 ? (
        <div className="py-16 text-center text-slate-400">
          <p className="font-medium">Chưa có thực phẩm trong kho</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <div
              ref={panelRef}
              className={
                filteredFoods.length === 0 || activeCategory || searching
                  ? "min-w-0 flex-1 rounded-2xl bg-white p-5 shadow-soft sm:p-6 lg:min-h-[24rem]"
                  : "min-w-0 flex-1 lg:min-h-[24rem]"
              }
            >
                {activeCategory ? (
                  <CategoryFoodPanel
                    category={activeCategory}
                    foods={pagedFoods}
                    total={categoryFoods.length}
                    page={page}
                    pages={pageCount}
                    searching={searching}
                    onSelect={selectFood}
                    onBack={showOverview}
                    onPage={goPage}
                  />
                ) : filteredFoods.length === 0 ? (
                  <div className="flex min-h-48 flex-col items-center justify-center text-center text-sm text-slate-400">
                    <p className="font-medium">Không tìm thấy thực phẩm</p>
                    <p className="mt-1">Thử ức gà, cơm trắng, chuối.</p>
                  </div>
                ) : searching ? (
                  <SearchResultsGrid
                    foods={pagedFoods}
                    total={filteredFoods.length}
                    page={page}
                    pages={pageCount}
                    slugByCategoryId={slugByCategoryId}
                    onSelect={selectFood}
                    onPage={goPage}
                  />
                ) : (
                  <OverviewAisles
                    categories={aisleCategories}
                    foodsByCategory={foodsByCategory}
                    onSelectCategory={selectCategory}
                    onSelectFood={selectFood}
                  />
                )}
              </div>
          </div>
        </>
      )}

      <Modal
        open={detailOpen && !!selected}
        onClose={closeFoodDetail}
        size="lg"
        title={selected ? foodDisplayName(selected.name_vi) : "Chi tiết thực phẩm"}
      >
        {selected ? (
          <FoodDetailPanel
            food={selected}
            category={
              (selected.category_id != null
                ? categories.find((c) => c.id === selected.category_id)
                : null) ?? activeCategory
            }
            onClose={closeFoodDetail}
          />
        ) : null}
      </Modal>
    </section>
  );
}

function OverviewAisles({
  categories,
  foodsByCategory,
  onSelectCategory,
  onSelectFood,
}: {
  categories: FoodCategory[];
  foodsByCategory: Map<number, Food[]>;
  onSelectCategory: (id: number) => void;
  onSelectFood: (food: Food) => void;
}) {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="type-title">Tất cả quầy</h2>
        <p className="mt-2 text-sm text-slate-500">Bấm vào ảnh để xem chi tiết calo.</p>
      </div>
      {categories.map((cat) => {
        const items = foodsByCategory.get(cat.id) || [];
        const withPhoto = items.filter((f) => f.image_url);
        const preview = (
          withPhoto.length >= 8 ? withPhoto : [...withPhoto, ...items.filter((f) => !f.image_url)]
        ).slice(0, 8);
        const theme = aisleTheme(cat.slug);
        return (
          <section key={cat.id} className="rounded-2xl bg-white p-4 shadow-soft sm:p-5">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex min-w-0 items-start gap-3">
                <span
                  className={`mt-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br ${theme.tile} ${theme.icon}`}
                >
                  <AisleIcon slug={cat.slug} className="h-5 w-5" />
                </span>
                <div className="min-w-0">
                  <h3 className="font-bold tracking-tight text-slate-900">{cat.name_vi}</h3>
                </div>
              </div>
              <button
                type="button"
                onClick={() => onSelectCategory(cat.id)}
                className="shrink-0 text-sm font-semibold text-brand-600 hover:underline"
              >
                Xem hết {items.length.toLocaleString("vi-VN")} món →
              </button>
            </div>
            {preview.length === 0 ? (
              <p className="mt-4 text-sm text-slate-400">Chưa có món trong quầy này.</p>
            ) : (
              <FoodCardGrid
                foods={preview}
                slugByCategoryId={{ [cat.id]: cat.slug }}
                onSelect={onSelectFood}
              />
            )}
          </section>
        );
      })}
    </div>
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

function FoodPager({
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
  const from = (page - 1) * FOOD_PAGE_SIZE + 1;
  const to = Math.min(page * FOOD_PAGE_SIZE, total);
  return (
    <nav className="mt-6 flex flex-wrap items-center justify-between gap-3" aria-label="Phân trang">
      <p className="text-sm text-slate-500">
        {from.toLocaleString("vi-VN")}–{to.toLocaleString("vi-VN")} / {total.toLocaleString("vi-VN")} món
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

function SearchResultsGrid({
  foods,
  total,
  page,
  pages,
  slugByCategoryId,
  onSelect,
  onPage,
}: {
  foods: Food[];
  total: number;
  page: number;
  pages: number;
  slugByCategoryId: Record<number, string>;
  onSelect: (food: Food) => void;
  onPage: (n: number) => void;
}) {
  return (
    <div>
      <h2 className="type-title">Kết quả tìm kiếm</h2>
      <p className="mt-2 text-sm text-slate-500">
        {total.toLocaleString("vi-VN")} thực phẩm khớp. Chọn món để xem calo.
      </p>
      <FoodCardGrid foods={foods} slugByCategoryId={slugByCategoryId} onSelect={onSelect} />
      <FoodPager page={page} pages={pages} total={total} onPage={onPage} />
    </div>
  );
}

function FoodCardGrid({
  foods,
  slugByCategoryId,
  onSelect,
  compact = false,
}: {
  foods: Food[];
  slugByCategoryId: Record<number, string>;
  onSelect: (food: Food) => void;
  compact?: boolean;
}) {
  return (
    <ul
      className={
        compact
          ? "mt-5 grid gap-4 sm:grid-cols-2"
          : "mt-5 grid grid-cols-2 gap-3 sm:gap-4 md:grid-cols-3 xl:grid-cols-4"
      }
    >
      {foods.map((food) => {
        const slug = (food.category_id != null && slugByCategoryId[food.category_id]) || "rau-cu-qua";
        return (
          <li key={food.id}>
            <button
              type="button"
              onClick={() => onSelect(food)}
              className="card-media-zoom flex h-full w-full flex-col overflow-hidden rounded-2xl bg-white text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <FoodVisual food={food} slug={slug} />
              <span className="flex flex-1 flex-col p-4">
                <span className="font-bold leading-snug text-slate-900">
                  {foodDisplayName(food.name_vi)}
                </span>
                <span className="mt-1 text-xs text-slate-500">{foodCardMeta(food)}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}

function CategoryFoodPanel({
  category,
  foods,
  total,
  page,
  pages,
  searching,
  onSelect,
  onBack,
  onPage,
}: {
  category: FoodCategory;
  foods: Food[];
  total: number;
  page: number;
  pages: number;
  searching: boolean;
  onSelect: (food: Food) => void;
  onBack: () => void;
  onPage: (n: number) => void;
}) {
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs font-medium text-brand-600 hover:underline"
        >
          ← Tất cả quầy
        </button>
        <span className="text-xs text-slate-400">{total} món</span>
      </div>
      <h2 className="mt-3 type-title">{category.name_vi}</h2>
      {searching ? (
        <p className="mt-1 text-sm text-slate-500">
          {total
            ? `${total} món khớp tìm kiếm trong quầy này.`
            : "Không có món khớp tìm kiếm trong quầy này."}
        </p>
      ) : null}
      {total === 0 ? (
        <p className="mt-8 text-sm text-slate-400">Chưa có món trong quầy này.</p>
      ) : (
        <>
          <FoodCardGrid
            foods={foods}
            slugByCategoryId={{ [category.id]: category.slug }}
            onSelect={onSelect}
          />
          <FoodPager page={page} pages={pages} total={total} onPage={onPage} />
        </>
      )}
    </div>
  );
}

function NutrientCol({
  title,
  data,
  carbLabel = "Tinh bột",
}: {
  title: string;
  data: FoodNutrients;
  carbLabel?: string;
}) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="type-kicker text-slate-400">{title}</p>
      <p className="type-stat mt-1 text-2xl leading-none text-brand-600">{viNum(data.calories)}</p>
      <p className="mt-0.5 text-xs text-slate-400">calo</p>
      <div className="mt-3">
        <MacroBar protein_g={data.protein_g} carbs_g={data.carbs_g} fat_g={data.fat_g} />
      </div>
      <div className="mt-2 space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Đạm</span>
          <span className="font-semibold">{viNum(data.protein_g)}g</span>
        </div>
        <div className="flex justify-between gap-3">
          <span className="text-slate-500">{carbLabel}</span>
          <span className="shrink-0 font-semibold">{viNum(data.carbs_g)}g</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Chất béo</span>
          <span className="font-semibold">{viNum(data.fat_g)}g</span>
        </div>
        {data.sugar_g != null && (
          <div className="flex justify-between">
            <span className="text-slate-500">Đường</span>
            <span className="font-semibold">{viNum(data.sugar_g)}g</span>
          </div>
        )}
        {data.sodium_mg != null && (
          <div className="flex justify-between">
            <span className="text-slate-500">Natri</span>
            <span className="font-semibold">{viNum(data.sodium_mg)}mg</span>
          </div>
        )}
      </div>
    </div>
  );
}

function FoodDetailPanel({
  food,
  category,
  onClose,
}: {
  food: Food;
  category: FoodCategory | null;
  onClose: () => void;
}) {
  const per100 = foodPer100g(food);
  const serving = foodServingNutrients(food);
  const sameAs100 = servingIs100g(food);
  const role = foodRoleLabel(food);
  const slug = category?.slug || ((food.food_kind || "") === "dish" ? "mon-an-truyen-thong" : "rau-cu-qua");
  const servingHint = food.serving_size?.trim();
  const carbLabel = "Tinh bột";
  const isDish = (food.food_kind || "") === "dish";

  return (
    <>
      <FoodVisual food={food} slug={slug} className="h-44 sm:h-52" eager />
      <div className="p-5">
        {role ? (
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="badge badge-gray">{role}</span>
          </div>
        ) : null}
        <h2 className="type-title">{foodDisplayName(food.name_vi)}</h2>
        {food.name_en && <p className="mt-0.5 text-sm text-slate-400">{food.name_en}</p>}
        {servingHint && <p className="mt-2 text-sm text-slate-600">Khẩu phần: {servingHint}</p>}
        {isDish && food.description_vi ? (
          <p className="mt-2 text-sm leading-relaxed text-slate-600">{food.description_vi}</p>
        ) : null}

        {sameAs100 || !per100 ? (
          <div className="mt-4">
            <NutrientCol title={`Theo ${food.serving_size || "100g"}`} data={serving} carbLabel={carbLabel} />
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
            <NutrientCol title="Theo 100g" data={per100} carbLabel={carbLabel} />
            <NutrientCol title={`Theo ${food.serving_size}`} data={serving} carbLabel={carbLabel} />
          </div>
        )}
        <FoodAmountConverter food={food} />
        {isDish ? (
          <Link
            href={cookPostHref(food.slug)}
            className="mt-4 inline-flex text-sm font-bold text-brand-700 hover:underline"
          >
            Cách nấu món này →
          </Link>
        ) : (
          <RecipesUsingFood slug={food.slug} />
        )}
        <button type="button" onClick={onClose} className="btn-brand mt-5 w-full">
          Đóng
        </button>
      </div>
    </>
  );
}

function RecipesUsingFood({ slug }: { slug: string }) {
  const [posts, setPosts] = useState<CookingPost[]>([]);
  useEffect(() => {
    let alive = true;
    cookingPostsApi
      .listPublic(1, 20, slug)
      .then((data) => {
        if (alive) setPosts(data.items || []);
      })
      .catch(() => {
        if (alive) setPosts([]);
      });
    return () => {
      alive = false;
    };
  }, [slug]);
  if (!posts.length) return null;
  return (
    <div className="mt-4">
      <p className="text-sm font-bold text-slate-800">Dùng trong cách nấu</p>
      <ul className="mt-2 space-y-1">
        {posts.map((post) => (
          <li key={post.slug}>
            <Link href={cookPostHref(post.slug)} className="text-sm font-semibold text-brand-700 hover:underline">
              {post.title_vi}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
