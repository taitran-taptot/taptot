"use client";

import { useEffect, useMemo, useRef, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { PAGE_SIZE } from "@/lib/config";
import {
  foodDisplayName,
  foodKcalLine,
  foodPer100g,
  foodRoleLabel,
  foodServingNutrients,
  servingIs100g,
  type FoodNutrients,
} from "@/lib/foodDisplay";
import { mediaUrl, viNum } from "@/lib/labels";
import type { Food, FoodCategory } from "@/lib/types";
import FoodAisleChips from "./FoodAisleChips";
import HomeCookingPosts from "./HomeCookingPosts";
import MacroBar from "./MacroBar";
import VietnamFoodMap from "./VietnamFoodMap";

type BrowseTab = "ingredients" | "dishes";
type AisleTheme = {
  tile: string;
  icon: string;
  blurb: string;
};

const AISLE: Record<string, AisleTheme> = {
  "thit-hai-san": {
    tile: "from-rose-100 to-orange-100",
    icon: "text-rose-700",
    blurb: "Đạm cho bữa — thịt, cá, tôm",
  },
  "trai-cay-rau-cu": {
    tile: "from-brand-100 to-emerald-50",
    icon: "text-brand-800",
    blurb: "Rau củ quả tươi, ít calo",
  },
  "mon-phu-an-vat": {
    tile: "from-amber-100 to-yellow-50",
    icon: "text-amber-800",
    blurb: "Cơm, khoai, bánh mì",
  },
  "trung-sua": {
    tile: "from-orange-50 to-amber-100",
    icon: "text-amber-900",
    blurb: "Trứng, sữa, yogurt",
  },
  "hat-dau": {
    tile: "from-slate-100 to-stone-100",
    icon: "text-slate-700",
    blurb: "Đậu phụ và dầu ăn",
  },
};

function aisleTheme(slug: string): AisleTheme {
  return (
    AISLE[slug] || {
      tile: "from-slate-100 to-slate-50",
      icon: "text-slate-600",
      blurb: "Thực phẩm trong kho",
    }
  );
}

function AisleIcon({ slug, className }: { slug: string; className?: string }) {
  const cls = `h-8 w-8 ${className || ""}`;
  if (slug === "thit-hai-san") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M4 14c2-6 8-8 14-5 1 4-1 8-5 9-4 1-8-1-9-4Z" />
        <path d="M8 12h.01M12 10h.01" />
      </svg>
    );
  }
  if (slug === "trai-cay-rau-cu") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M12 21c4-2 7-7 7-11a7 7 0 1 0-14 0c0 4 3 9 7 11Z" />
        <path d="M12 10V4" />
      </svg>
    );
  }
  if (slug === "mon-phu-an-vat") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M4 11h16l-1.2 7.2A2 2 0 0 1 16.8 20H7.2a2 2 0 0 1-2-1.8L4 11Z" />
        <path d="M8 11V8a4 4 0 0 1 8 0v3" />
      </svg>
    );
  }
  if (slug === "trung-sua") {
    return (
      <svg className={cls} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8} aria-hidden>
        <path d="M12 4c3.5 0 6 4.2 6 8.5S15.5 20 12 20 6 16.8 6 12.5 8.5 4 12 4Z" />
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
}: {
  food?: Food | null;
  slug: string;
  className?: string;
}) {
  const theme = aisleTheme(slug);
  const src = mediaUrl(food?.image_url);
  return (
    <div className={`overflow-hidden bg-gradient-to-br ${theme.tile} ${className}`}>
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={src} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className={`grid h-full place-items-center ${theme.icon}`}>
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
    ? `${viNum(per100?.calories ?? food.calories)} kcal / 100g`
    : foodKcalLine(food);
  return [role, kcalPart].filter(Boolean).join(" · ");
}

function sortAisleFoods(items: Food[]): Food[] {
  return [...items].sort((a, b) => {
    if (a.is_common !== b.is_common) return a.is_common ? -1 : 1;
    return foodDisplayName(a.name_vi).localeCompare(foodDisplayName(b.name_vi), "vi");
  });
}

async function loadAllFoods(): Promise<Food[]> {
  const pageSize = 100;
  const first = await api.searchFoods({ page: 1, page_size: pageSize });
  const items = [...first.items];
  for (let page = 2; page <= first.pages; page++) {
    const data = await api.searchFoods({ page, page_size: pageSize });
    items.push(...data.items);
  }
  return items;
}

function sameProvinceId(a?: string | null, b?: string | null): boolean {
  if (!a || !b) return false;
  const left = a.trim();
  const right = b.trim();
  if (left === right) return true;
  if (/^\d+$/.test(left) && /^\d+$/.test(right)) {
    return left.padStart(2, "0") === right.padStart(2, "0");
  }
  return false;
}

function matchesQuery(food: Food, query: string): boolean {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  return (
    food.name_vi.toLowerCase().includes(q) ||
    foodDisplayName(food.name_vi).toLowerCase().includes(q) ||
    (food.name_en?.toLowerCase().includes(q) ?? false)
  );
}

export default function FoodLibrary({ cookBase = "/cach-nau" }: { cookBase?: string }) {
  return (
    <Suspense fallback={<div className="py-16 text-center text-sm text-slate-400">Đang tải…</div>}>
      <FoodLibraryInner cookBase={cookBase} />
    </Suspense>
  );
}

function FoodLibraryInner({ cookBase = "/cach-nau" }: { cookBase?: string }) {
  const searchParams = useSearchParams();
  const initialTab: BrowseTab =
    searchParams.get("tab") === "dishes" ? "dishes" : "ingredients";
  const [categories, setCategories] = useState<FoodCategory[]>([]);
  const [foods, setFoods] = useState<Food[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [q, setQ] = useState("");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);
  const [browseTab, setBrowseTab] = useState<BrowseTab>(initialTab);
  const [provinceFilter, setProvinceFilter] = useState<{ id: string; name: string } | null>(null);
  const [provinceNames, setProvinceNames] = useState<Record<string, string>>({});
  const [mapPopupOpen, setMapPopupOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const tab = searchParams.get("tab");
    if (tab === "dishes") setBrowseTab("dishes");
    else if (tab === "ingredients") setBrowseTab("ingredients");
  }, [searchParams]);

  useEffect(() => {
    fetch("/maps/vietnam-food-map.json")
      .then((r) => (r.ok ? r.json() : null))
      .then((json: { features?: { id: string; name: string }[] } | null) => {
        if (!json?.features) return;
        setProvinceNames(Object.fromEntries(json.features.map((f) => [f.id, f.name])));
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    Promise.all([api.foodCategories(), loadAllFoods()])
      .then(([catRes, allFoods]) => {
        const sorted = [...catRes.items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        setCategories(sorted);
        setFoods(sortAisleFoods(allFoods));
      })
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (q.trim()) setSelectedId(null);
    setPage(1);
  }, [q]);

  useEffect(() => {
    setPage(1);
  }, [selectedCategoryId, browseTab, provinceFilter]);

  const aisleCategories = useMemo(
    () => categories.filter((c) => c.slug !== "mon-an"),
    [categories],
  );

  const ingredientFoods = useMemo(
    () => foods.filter((f) => (f.food_kind || "ingredient") !== "dish"),
    [foods],
  );

  const traditionalDishes = useMemo(
    () =>
      foods.filter(
        (f) => (f.food_kind || "") === "dish" && Boolean(f.province_id || f.region_slug),
      ),
    [foods],
  );

  const tabFoods = browseTab === "ingredients" ? ingredientFoods : traditionalDishes;

  const filteredFoods = useMemo(() => {
    let list = tabFoods.filter((f) => matchesQuery(f, q));
    if (browseTab === "dishes" && provinceFilter) {
      list = list.filter((f) => sameProvinceId(f.province_id, provinceFilter.id));
    }
    return list;
  }, [tabFoods, q, browseTab, provinceFilter]);

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

  const searching = Boolean(q.trim());
  const dishList = useMemo(() => sortAisleFoods(filteredFoods), [filteredFoods]);
  const gridList =
    browseTab === "dishes"
      ? dishList
      : searching && selectedCategoryId == null
        ? filteredFoods
        : categoryFoods;
  const pageCount = Math.max(1, Math.ceil(gridList.length / PAGE_SIZE));
  const pagedFoods = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return gridList.slice(start, start + PAGE_SIZE);
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
    if (browseTab === "ingredients" && food.category_id != null) {
      setSelectedCategoryId(food.category_id);
    }
    if (browseTab === "dishes") {
      if (food.province_id) {
        setProvinceFilter({
          id: food.province_id,
          name: provinceNames[food.province_id] || food.province_id,
        });
      }
      setMapPopupOpen(true);
    }
  }

  function selectCategory(id: number) {
    setSelectedCategoryId(id);
    setSelectedId(null);
    setMapPopupOpen(false);
  }

  function showOverview() {
    setSelectedId(null);
    setSelectedCategoryId(null);
    setMapPopupOpen(false);
  }

  function onChipSelect(next: number | "") {
    if (next === "") showOverview();
    else selectCategory(next);
  }

  function switchTab(tab: BrowseTab) {
    setBrowseTab(tab);
    setQ("");
    setSelectedId(null);
    setSelectedCategoryId(null);
    setProvinceFilter(null);
    setMapPopupOpen(false);
    setPage(1);
  }

  const mapMode = browseTab === "ingredients" ? "nationwide" : "region";
  const mapProvinceId =
    browseTab === "dishes" ? selected?.province_id || provinceFilter?.id || null : null;
  const mapDishLabel =
    browseTab === "dishes" && selected ? foodDisplayName(selected.name_vi) : null;
  const dishCountByProvince = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const food of traditionalDishes) {
      const id = food.province_id?.trim();
      if (!id) continue;
      const key = /^\d+$/.test(id) ? id.padStart(2, "0") : id;
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }, [traditionalDishes]);

  const provinceDishCount = provinceFilter
    ? traditionalDishes.filter((f) => sameProvinceId(f.province_id, provinceFilter.id)).length
    : 0;

  function provinceNameOf(id?: string | null) {
    if (!id) return "Việt Nam";
    if (provinceNames[id]) return provinceNames[id];
    if (provinceFilter?.id === id) return provinceFilter.name;
    return id;
  }

  const showDishPopup = browseTab === "dishes" && mapPopupOpen && selected;

  return (
    <section>
      <div className="mb-5">
        <h1 className="text-2xl font-extrabold tracking-tight">Thư viện thực phẩm Việt</h1>
        <p className="mt-1 text-sm text-slate-500">
          Thịt, rau, cơm — và món truyền thống theo từng tỉnh trên bản đồ.
        </p>
      </div>

      <div className="mb-4 flex gap-2 rounded-2xl bg-white p-1.5 shadow-soft">
        {(
          [
            { id: "ingredients" as const, label: "Thực phẩm" },
            { id: "dishes" as const, label: "Món truyền thống" },
          ] as const
        ).map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => switchTab(t.id)}
            className={`flex-1 rounded-xl px-3 py-2.5 text-sm font-bold transition ${
              browseTab === t.id
                ? "bg-brand-500 text-white shadow-soft"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

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
            placeholder={
              browseTab === "dishes"
                ? "Tìm món… (vd: phở, mì Quảng, bánh xèo)"
                : "Tìm… (vd: ức gà, cơm trắng, chuối)"
            }
            className="field pl-10"
          />
        </div>
        {browseTab === "ingredients" && (
          <div className="lg:hidden">
            <FoodAisleChips
              categories={chipCategories}
              allCount={filteredFoods.length}
              counts={aisleCounts}
              selected={selectedCategoryId ?? ""}
              onSelect={onChipSelect}
            />
          </div>
        )}
        {browseTab === "dishes" && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setProvinceFilter(null);
                setSelectedId(null);
                setMapPopupOpen(false);
              }}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                provinceFilter == null ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600"
              }`}
            >
              Tất cả tỉnh
            </button>
            {provinceFilter && (
              <button
                type="button"
                className="rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white"
              >
                {provinceFilter.name} · {provinceDishCount} món
              </button>
            )}
          </div>
        )}
      </div>

      {error && <div className="py-12 text-center text-rose-500">Lỗi tải dữ liệu: {error}</div>}

      {loading ? (
        <div className="flex flex-col gap-4 lg:flex-row">
          <div className="h-80 w-full animate-pulse rounded-2xl bg-white shadow-soft lg:w-[42%]" />
          <div className="min-h-80 flex-1 animate-pulse rounded-2xl bg-white shadow-soft" />
        </div>
      ) : foods.length === 0 ? (
        <div className="py-16 text-center text-slate-400">
          <p className="font-medium">Chưa có thực phẩm trong kho</p>
        </div>
      ) : (
        <>
          <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
            <div className="flex min-w-0 flex-col gap-4 lg:w-[42%] lg:shrink-0">
              {browseTab === "ingredients" && (
                <aside className="hidden w-full rounded-2xl bg-white shadow-soft lg:sticky lg:top-20 lg:block">
                  <nav className="p-2" aria-label="Quầy thực phẩm">
                    <button
                      type="button"
                      onClick={showOverview}
                      className={`mb-1 w-full rounded-xl px-3 py-2.5 text-left text-sm transition ${
                        selectedId == null && selectedCategoryId == null
                          ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                          : "text-slate-700 hover:bg-slate-50"
                      }`}
                    >
                      <span className="block">Tổng quan</span>
                      <span className="text-xs font-medium text-slate-400">
                        {filteredFoods.length.toLocaleString("vi-VN")} thực phẩm
                      </span>
                    </button>
                    {aisleCategories.map((cat) => {
                      const n = aisleCounts[cat.id] || 0;
                      if (searching && n === 0) return null;
                      const active = selectedCategoryId === cat.id;
                      return (
                        <button
                          key={cat.id}
                          type="button"
                          onClick={() => selectCategory(cat.id)}
                          className={`mb-0.5 flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2.5 text-left text-sm transition ${
                            active
                              ? "bg-brand-50 font-semibold text-brand-800 ring-1 ring-brand-100"
                              : "text-slate-700 hover:bg-slate-50"
                          }`}
                        >
                          <span className="min-w-0 leading-snug">{cat.name_vi}</span>
                          <span className="shrink-0 text-xs font-medium text-slate-400">{n}</span>
                        </button>
                      );
                    })}
                  </nav>
                </aside>
              )}

              <div
                ref={panelRef}
                className={
                  selected || filteredFoods.length === 0 || browseTab === "dishes"
                    ? "min-w-0 flex-1 rounded-2xl bg-white p-5 shadow-soft sm:p-6 lg:min-h-[24rem]"
                    : "min-w-0 flex-1 lg:min-h-[24rem]"
                }
              >
                {browseTab === "dishes" ? (
                  selected && !showDishPopup ? (
                    <FoodDetailPanel
                      food={selected}
                      category={null}
                      onBack={() => {
                        setSelectedId(null);
                        setMapPopupOpen(false);
                      }}
                    />
                  ) : (
                    <div>
                      <h2 className="text-xl font-extrabold tracking-tight">Món truyền thống</h2>
                      <p className="mt-1 text-sm text-slate-500">
                        Chọn món để sáng tỉnh trên bản đồ. Bấm tỉnh trên bản đồ để lọc.
                      </p>
                      {dishList.length === 0 ? (
                        <p className="mt-8 text-sm text-slate-400">
                          {provinceFilter
                            ? "Chưa có món cho tỉnh này"
                            : "Chưa có món khớp."}
                        </p>
                      ) : (
                        <>
                          <FoodCardGrid
                            foods={pagedFoods}
                            slugByCategoryId={slugByCategoryId}
                            onSelect={selectFood}
                          />
                          <FoodPager page={page} pages={pageCount} total={dishList.length} onPage={goPage} />
                        </>
                      )}
                    </div>
                  )
                ) : selected ? (
                  <FoodDetailPanel
                    food={selected}
                    category={activeCategory}
                    onBack={() => setSelectedId(null)}
                  />
                ) : activeCategory ? (
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
                  />
                )}
              </div>
            </div>

            <div className="relative min-w-0 flex-1 lg:sticky lg:top-20">
              <VietnamFoodMap
                mode={mapMode}
                activeProvinceId={mapProvinceId}
                dishLabel={mapDishLabel}
                dishCountByProvince={dishCountByProvince}
                onProvinceClick={
                  browseTab === "dishes"
                    ? ({ id, name }) => {
                        setProvinceFilter({ id, name });
                        setSelectedId(null);
                        setMapPopupOpen(false);
                      }
                    : undefined
                }
                className="min-h-[28rem] shadow-soft ring-1 ring-slate-100"
              />
              {showDishPopup && selected && (
                <div className="absolute inset-x-4 bottom-4 z-10 rounded-2xl bg-white p-4 shadow-lg ring-1 ring-slate-200 sm:inset-x-auto sm:right-4 sm:bottom-auto sm:top-4 sm:w-72">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-xs font-semibold text-brand-600">
                        {provinceNameOf(selected.province_id)}
                      </p>
                      <h3 className="mt-0.5 text-base font-extrabold text-slate-900">
                        {foodDisplayName(selected.name_vi)}
                      </h3>
                    </div>
                    <button
                      type="button"
                      onClick={() => setMapPopupOpen(false)}
                      className="rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-100"
                      aria-label="Đóng"
                    >
                      Đóng
                    </button>
                  </div>
                  {mediaUrl(selected.image_url) ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={mediaUrl(selected.image_url)!}
                      alt=""
                      className="mt-3 h-28 w-full rounded-xl object-cover"
                    />
                  ) : (
                    <div className="mt-3 grid h-28 place-items-center rounded-xl bg-gradient-to-br from-brand-100 to-emerald-50 text-sm font-semibold text-brand-700">
                      {provinceNameOf(selected.province_id)}
                    </div>
                  )}
                  <p className="mt-3 text-sm leading-relaxed text-slate-600">
                    {selected.description_vi || "Món truyền thống Việt Nam."}
                  </p>
                  <button
                    type="button"
                    onClick={() => setMapPopupOpen(false)}
                    className="mt-3 w-full rounded-xl bg-brand-50 py-2 text-sm font-bold text-brand-700 hover:bg-brand-100"
                  >
                    Xem chi tiết calo
                  </button>
                </div>
              )}
            </div>
          </div>

          {browseTab === "ingredients" && !selected && !activeCategory && !searching && (
            <div className="mt-8">
              <HomeCookingPosts
                basePath={cookBase}
                compact
                title="Cách nấu món Việt"
                cta="Xem hết công thức"
              />
            </div>
          )}
        </>
      )}
    </section>
  );
}

function OverviewAisles({
  categories,
  foodsByCategory,
  onSelectCategory,
}: {
  categories: FoodCategory[];
  foodsByCategory: Map<number, Food[]>;
  onSelectCategory: (id: number) => void;
}) {
  return (
    <div>
      <h2 className="text-xl font-extrabold tracking-tight">Chọn quầy</h2>
      <p className="mt-2 text-sm text-slate-500">
        Như đi chợ: vào đúng quầy rồi chọn thực phẩm để xem calo.
      </p>
      <div className="mt-5 grid gap-4 sm:grid-cols-2">
        {categories.map((cat) => {
          const items = foodsByCategory.get(cat.id) || [];
          const theme = aisleTheme(cat.slug);
          return (
            <button
              key={cat.id}
              type="button"
              onClick={() => onSelectCategory(cat.id)}
              className="animate-in overflow-hidden rounded-2xl bg-white text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <div className={`flex h-28 items-center justify-center bg-gradient-to-br ${theme.tile}`}>
                <span className={theme.icon}>
                  <AisleIcon slug={cat.slug} className="h-12 w-12" />
                </span>
              </div>
              <div className="p-4">
                <p className="font-bold leading-snug">{cat.name_vi}</p>
                <p className="mt-1 text-sm text-slate-500">{theme.blurb}</p>
                <p className="mt-2 text-xs font-semibold text-brand-600">
                  {items.length.toLocaleString("vi-VN")} món →
                </p>
              </div>
            </button>
          );
        })}
      </div>
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
  const from = (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);
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
      <h2 className="text-xl font-extrabold tracking-tight">Kết quả tìm kiếm</h2>
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
}: {
  foods: Food[];
  slugByCategoryId: Record<number, string>;
  onSelect: (food: Food) => void;
}) {
  return (
    <ul className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {foods.map((food) => {
        const slug = (food.category_id != null && slugByCategoryId[food.category_id]) || "hat-dau";
        return (
          <li key={food.id}>
            <button
              type="button"
              onClick={() => onSelect(food)}
              className="flex h-full w-full flex-col overflow-hidden rounded-2xl bg-white text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
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
  const theme = aisleTheme(category.slug);
  return (
    <div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs font-medium text-brand-600 hover:underline"
        >
          ← Tổng quan
        </button>
        <span className="text-xs text-slate-400">{total} món</span>
      </div>
      <h2 className="mt-3 text-xl font-extrabold leading-snug tracking-tight">{category.name_vi}</h2>
      <p className="mt-1 text-sm text-slate-500">
        {searching
          ? total
            ? `${total} món khớp tìm kiếm trong quầy này.`
            : "Không có món khớp tìm kiếm trong quầy này."
          : theme.blurb}
      </p>
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

function NutrientCol({ title, data }: { title: string; data: FoodNutrients }) {
  return (
    <div className="rounded-xl bg-slate-50 p-3">
      <p className="text-[11px] font-semibold tracking-wide text-slate-400 uppercase">{title}</p>
      <p className="mt-1 text-2xl leading-none font-extrabold text-brand-600">{viNum(data.calories)}</p>
      <p className="mt-0.5 text-xs text-slate-400">kcal</p>
      <div className="mt-3">
        <MacroBar protein_g={data.protein_g} carbs_g={data.carbs_g} fat_g={data.fat_g} />
      </div>
      <div className="mt-2 space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-slate-500">Đạm</span>
          <span className="font-semibold">{viNum(data.protein_g)}g</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Tinh bột</span>
          <span className="font-semibold">{viNum(data.carbs_g)}g</span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500">Chất béo</span>
          <span className="font-semibold">{viNum(data.fat_g)}g</span>
        </div>
        {data.fiber_g != null && (
          <div className="flex justify-between">
            <span className="text-slate-500">Chất xơ</span>
            <span className="font-semibold">{viNum(data.fiber_g)}g</span>
          </div>
        )}
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
  onBack,
}: {
  food: Food;
  category: FoodCategory | null;
  onBack: () => void;
}) {
  const per100 = foodPer100g(food);
  const serving = foodServingNutrients(food);
  const sameAs100 = servingIs100g(food);
  const role = foodRoleLabel(food);
  const raw = (food.prep_state || "").toLowerCase() === "raw";
  const slug = category?.slug || "hat-dau";
  const backLabel = category ? `← ${category.name_vi}` : "← Tổng quan";
  const servingHint = food.serving_size?.trim();

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs font-medium text-brand-600 hover:underline"
        >
          {backLabel}
        </button>
        {role && <span className="badge badge-gray">{role}</span>}
      </div>
      <FoodVisual food={food} slug={slug} className="mt-3 h-44 rounded-2xl sm:h-52" />
      <h2 className="mt-4 text-xl font-extrabold leading-snug tracking-tight">
        {foodDisplayName(food.name_vi)}
      </h2>
      {food.name_en && <p className="mt-0.5 text-sm text-slate-400">{food.name_en}</p>}
      {servingHint && (
        <p className="mt-2 text-sm text-slate-600">Khẩu phần quen: {servingHint}</p>
      )}

      {raw && (
        <p className="mt-3 rounded-xl bg-slate-50 px-3 py-2 text-sm text-slate-600">
          Số liệu lúc sống. Nấu như bình thường (luộc, nướng, xào ít dầu).
        </p>
      )}

      {sameAs100 || !per100 ? (
        <div className="mt-4">
          <NutrientCol title={`Theo ${food.serving_size || "100g"}`} data={serving} />
        </div>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          <NutrientCol title="Theo 100g" data={per100} />
          <NutrientCol title={`Theo ${food.serving_size}`} data={serving} />
        </div>
      )}
    </>
  );
}
