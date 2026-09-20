"use client";

import { useEffect, useMemo, useRef, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import {
  collectSubgroups,
  foodDisplayName,
  foodKcalLine,
  foodPer100g,
  foodRoleLabel,
  foodServingNutrients,
  foodSubgroup,
  isDishCategorySlug,
  isHiddenFoodCategorySlug,
  servingIs100g,
  type FoodNutrients,
} from "@/lib/foodDisplay";
import { mediaUrl, viNum } from "@/lib/labels";
import type { Food, FoodCategory } from "@/lib/types";
import FoodAisleChips from "./FoodAisleChips";
import HomeCookingPosts from "./HomeCookingPosts";
import MacroBar from "./MacroBar";
import VietnamFoodMap from "./VietnamFoodMap";

const FOOD_PAGE_SIZE = 24;
const HIDDEN_DISH_SUBGROUP_SLUGS = new Set(["banh-mi-mon-cuon", "mon-nuoc-soi"]);

type BrowseTab = "ingredients" | "dishes";
type AisleTheme = {
  tile: string;
  icon: string;
  blurb: string;
};

const AISLE: Record<string, AisleTheme> = {
  "rau-cu-qua": {
    tile: "from-brand-100 to-emerald-50",
    icon: "text-brand-800",
    blurb: "Rau, củ, quả tươi theo mùa",
  },
  "thit-gia-cam-noi-tang": {
    tile: "from-rose-100 to-orange-100",
    icon: "text-rose-700",
    blurb: "Thịt heo, bò, gà và nội tạng",
  },
  "ca-thuy-hai-san": {
    tile: "from-sky-100 to-cyan-50",
    icon: "text-sky-800",
    blurb: "Cá, tôm, cua, ốc và hải sản",
  },
  "trung-whey": {
    tile: "from-orange-50 to-amber-100",
    icon: "text-amber-900",
    blurb: "Trứng và whey protein",
  },
  "ngu-coc-hat": {
    tile: "from-amber-50 to-lime-50",
    icon: "text-amber-800",
    blurb: "Gạo, yến mạch và hạt",
  },
  "mon-an-truyen-thong": {
    tile: "from-amber-100 to-yellow-50",
    icon: "text-amber-800",
    blurb: "Phở, bún, cơm và món Việt",
  },
  "an-vat-do-uong": {
    tile: "from-violet-50 to-fuchsia-50",
    icon: "text-violet-800",
    blurb: "Ăn vặt, bánh kẹo và đồ uống",
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

function dishKcalLabel(food: Food): string {
  const serving = (food.serving_size || "").trim();
  const short = serving && serving.length <= 18 ? serving : "";
  return short ? `${viNum(food.calories)} kcal / ${short}` : `${viNum(food.calories)} kcal`;
}

type DishGroup = { slug: string; nameVi: string; items: Food[] };

function groupDishes(foods: Food[]): DishGroup[] {
  const map = new Map<string, DishGroup>();
  const ungrouped: Food[] = [];
  for (const food of foods) {
    const g = foodSubgroup(food);
    if (!g) {
      ungrouped.push(food);
      continue;
    }
    const row = map.get(g.slug);
    if (row) row.items.push(food);
    else map.set(g.slug, { slug: g.slug, nameVi: g.nameVi, items: [food] });
  }
  const groups = [...map.values()].sort((a, b) => a.nameVi.localeCompare(b.nameVi, "vi"));
  if (ungrouped.length) groups.push({ slug: "khac", nameVi: "Món khác", items: ungrouped });
  return groups;
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
  for (let page = 2; page <= first.pages; page++) {
    if (signal?.aborted) throw new DOMException("Aborted", "AbortError");
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
  const nameVi = (food.name_vi || "").toLowerCase();
  const display = foodDisplayName(food.name_vi).toLowerCase();
  const nameEn = (food.name_en || "").toLowerCase();
  return nameVi.includes(q) || display.includes(q) || nameEn.includes(q);
}

export default function FoodLibrary({ cookBase = "/cach-nau" }: { cookBase?: string }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setReady(true);
  }, []);
  if (!ready) {
    return <div className="py-16 text-center text-sm text-slate-400">Đang tải…</div>;
  }
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
  const [selectedSubgroup, setSelectedSubgroup] = useState("");
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
    if (q.trim()) {
      setSelectedId(null);
      setSelectedCategoryId(null);
      setSelectedSubgroup("");
    }
    setPage(1);
  }, [q]);

  useEffect(() => {
    setPage(1);
  }, [selectedCategoryId, selectedSubgroup, browseTab, provinceFilter]);

  useEffect(() => {
    if (browseTab === "dishes" && HIDDEN_DISH_SUBGROUP_SLUGS.has(selectedSubgroup)) {
      setSelectedSubgroup("");
    }
  }, [browseTab, selectedSubgroup]);

  const aisleCategories = useMemo(
    () =>
      categories.filter(
        (c) => !isDishCategorySlug(c.slug) && !isHiddenFoodCategorySlug(c.slug),
      ),
    [categories],
  );

  const ingredientFoods = useMemo(
    () => foods.filter((f) => (f.food_kind || "ingredient") !== "dish"),
    [foods],
  );

  const traditionalDishes = useMemo(
    () => foods.filter((f) => (f.food_kind || "") === "dish"),
    [foods],
  );

  const tabFoods = browseTab === "ingredients" ? ingredientFoods : traditionalDishes;

  const filteredFoods = useMemo(() => {
    let list = tabFoods.filter((f) => matchesQuery(f, q));
    if (browseTab === "dishes" && provinceFilter) {
      const matched = list.filter((f) => sameProvinceId(f.province_id, provinceFilter.id));
      // If a province has no dishes yet, keep the unfiltered list instead of an empty trap.
      if (matched.length > 0) list = matched;
    }
    if (selectedSubgroup) {
      list = list.filter((f) => foodSubgroup(f)?.slug === selectedSubgroup);
    }
    return list;
  }, [tabFoods, q, browseTab, provinceFilter, selectedSubgroup]);

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

  const subgroupOptions = useMemo(() => {
    if (browseTab === "dishes") {
      return collectSubgroups(traditionalDishes.filter((f) => matchesQuery(f, q))).filter(
        (g) => !HIDDEN_DISH_SUBGROUP_SLUGS.has(g.slug),
      );
    }
    return collectSubgroups(categoryFoods);
  }, [browseTab, traditionalDishes, categoryFoods, q]);

  const searching = Boolean(q.trim());
  const dishList = useMemo(() => sortAisleFoods(filteredFoods), [filteredFoods]);

  const gridList =
    browseTab === "dishes"
      ? dishList
      : searching && selectedCategoryId == null
        ? filteredFoods
        : categoryFoods;
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
    if (browseTab === "dishes") {
      if (selectedId === food.id && mapPopupOpen) {
        setMapPopupOpen(false);
        return;
      }
      setSelectedId(food.id);
      setMapPopupOpen(true);
      return;
    }
    setSelectedId(food.id);
    // Only pin the aisle when already inside one, so Back from overview/search
    // returns there instead of swapping a photo grid for the full unfiltered list.
    if (food.category_id != null && selectedCategoryId != null) {
      setSelectedCategoryId(food.category_id);
    }
  }

  function selectCategory(id: number) {
    setSelectedCategoryId(id);
    setSelectedSubgroup("");
    setSelectedId(null);
    setMapPopupOpen(false);
  }

  function showOverview() {
    setSelectedId(null);
    setSelectedCategoryId(null);
    setSelectedSubgroup("");
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
    setSelectedSubgroup("");
    setProvinceFilter(null);
    setMapPopupOpen(false);
    setPage(1);
  }

  const mapProvinceId =
    browseTab === "dishes" ? selected?.province_id || provinceFilter?.id || null : null;
  const mapNationwide =
    browseTab === "dishes" && Boolean(selectedSubgroup) && !provinceFilter && !selected;
  const dishSubgroupLabel =
    subgroupOptions.find((g) => g.slug === selectedSubgroup)?.nameVi ?? null;
  const dishCountByProvince = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const food of dishList) {
      const id = food.province_id?.trim();
      if (!id) continue;
      const key = /^\d+$/.test(id) ? id.padStart(2, "0") : id;
      counts[key] = (counts[key] || 0) + 1;
    }
    return counts;
  }, [dishList]);

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
        <h1 className="text-2xl font-extrabold tracking-tight">
          {browseTab === "dishes" ? "Món truyền thống Việt" : "Thư viện thực phẩm Việt"}
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          {browseTab === "dishes"
            ? "Bấm tỉnh trên bản đồ để lọc. Bấm món để sáng tỉnh và xem calo."
            : "Thịt, rau, cá, trứng — vào quầy như đi chợ, bấm món để xem calo."}
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
        {browseTab === "ingredients" && selectedCategoryId != null && subgroupOptions.length > 0 && (
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
        {browseTab === "dishes" && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setProvinceFilter(null);
                setSelectedSubgroup("");
                setSelectedId(null);
                setMapPopupOpen(false);
              }}
              className={`rounded-full px-3 py-1 text-xs font-semibold ${
                selectedSubgroup === "" && provinceFilter == null
                  ? "bg-brand-500 text-white"
                  : "bg-slate-100 text-slate-600"
              }`}
            >
              Tất cả
            </button>
            {subgroupOptions.map((g) => (
              <button
                key={g.slug}
                type="button"
                onClick={() => {
                  setSelectedSubgroup(g.slug);
                  setProvinceFilter(null);
                  setSelectedId(null);
                  setMapPopupOpen(false);
                }}
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  selectedSubgroup === g.slug ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600"
                }`}
              >
                {g.nameVi}
              </button>
            ))}
            {provinceFilter && (
              <button
                type="button"
                onClick={() => setProvinceFilter(null)}
                className="rounded-full bg-brand-500 px-3 py-1 text-xs font-semibold text-white"
              >
                {provinceFilter.name} · bỏ lọc tỉnh ✕
              </button>
            )}
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
            {browseTab === "dishes" && (
              <div className="relative min-w-0 flex-1 lg:sticky lg:top-20">
                <VietnamFoodMap
                  mode={mapNationwide ? "nationwide" : "region"}
                  activeProvinceId={mapNationwide ? null : mapProvinceId}
                  dishLabel={mapNationwide ? dishSubgroupLabel : null}
                  dishCountByProvince={dishCountByProvince}
                  onProvinceClick={({ id, name }) => {
                    setProvinceFilter({ id, name });
                    setSelectedId(null);
                    setMapPopupOpen(false);
                  }}
                  className="h-[min(72vh,30rem)] shadow-soft ring-1 ring-slate-100 sm:h-[32rem] lg:h-[min(72vh,680px)]"
                />
                {showDishPopup && selected && (
                  <div className="absolute inset-x-3 bottom-3 z-10 rounded-2xl bg-white p-3.5 shadow-lg ring-1 ring-slate-200 sm:inset-x-auto sm:right-3 sm:bottom-auto sm:top-3 sm:w-72">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
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
                        className="shrink-0 rounded-lg px-2 py-1 text-xs font-semibold text-slate-500 hover:bg-slate-100"
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
                    ) : null}
                    <p className="mt-2 text-sm font-bold text-brand-700">{dishKcalLabel(selected)}</p>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600">
                      {selected.description_vi || "Món truyền thống Việt Nam."}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div
              ref={panelRef}
              className={
                browseTab === "dishes"
                  ? "min-w-0 rounded-2xl bg-white p-4 shadow-soft sm:p-5 lg:w-[26rem] lg:shrink-0 xl:w-[28rem] lg:max-h-[min(72vh,680px)] lg:overflow-y-auto"
                  : selected || filteredFoods.length === 0 || activeCategory || searching
                    ? "min-w-0 flex-1 rounded-2xl bg-white p-5 shadow-soft sm:p-6 lg:min-h-[24rem]"
                    : "min-w-0 flex-1 lg:min-h-[24rem]"
              }
            >
                {browseTab === "dishes" ? (
                  <DishMenuList
                    foods={dishList}
                    selectedId={selectedId}
                    provinceLabel={provinceFilter?.name ?? null}
                    provinceNameOf={provinceNameOf}
                    onSelect={selectFood}
                  />
                ) : selected ? (
                  <FoodDetailPanel
                    food={selected}
                    category={
                      (selected.category_id != null
                        ? categories.find((c) => c.id === selected.category_id)
                        : null) ?? activeCategory
                    }
                    backLabel={
                      activeCategory
                        ? `← ${activeCategory.name_vi}`
                        : searching
                          ? "← Kết quả tìm kiếm"
                          : "← Tất cả quầy"
                    }
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
                    onSelectFood={selectFood}
                  />
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

function DishThumb({ food }: { food: Food }) {
  const src = mediaUrl(food.image_url);
  const [failedSrc, setFailedSrc] = useState<string | null>(null);
  const showPhoto = Boolean(src) && failedSrc !== src;
  return (
    <span className="relative h-14 w-14 shrink-0 overflow-hidden rounded-xl bg-gradient-to-br from-amber-100 to-orange-50">
      {src ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={src}
          alt=""
          loading="lazy"
          decoding="async"
          className={`h-full w-full object-cover ${showPhoto ? "" : "invisible"}`}
          onLoad={() => setFailedSrc((prev) => (prev === src ? null : prev))}
          onError={() => {
            if (src) setFailedSrc(src);
          }}
        />
      ) : null}
      {!showPhoto && (
        <span className="absolute inset-0 grid place-items-center text-amber-800">
          <AisleIcon slug="mon-an-truyen-thong" className="h-7 w-7" />
        </span>
      )}
    </span>
  );
}

function DishMenuList({
  foods,
  selectedId,
  provinceLabel,
  provinceNameOf,
  onSelect,
}: {
  foods: Food[];
  selectedId: number | null;
  provinceLabel: string | null;
  provinceNameOf: (id?: string | null) => string;
  onSelect: (food: Food) => void;
}) {
  const listRef = useRef<HTMLDivElement>(null);
  const groups = useMemo(() => groupDishes(foods), [foods]);

  useEffect(() => {
    if (selectedId == null) return;
    const el = listRef.current?.querySelector(`[data-dish-id="${selectedId}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [selectedId]);

  return (
    <div ref={listRef}>
      <div className="flex items-end justify-between gap-3">
        <h2 className="text-lg font-extrabold tracking-tight">
          {provinceLabel || "Danh sách món"}
        </h2>
        <p className="text-xs font-semibold text-slate-400">
          {foods.length.toLocaleString("vi-VN")} món
        </p>
      </div>
      {foods.length === 0 ? (
        <p className="mt-8 text-sm text-slate-400">
          {provinceLabel ? "Chưa có món cho tỉnh này." : "Chưa có món khớp."}
        </p>
      ) : (
        <div className="mt-3 space-y-4">
          {groups.map((group) => (
            <section key={group.slug}>
              {groups.length > 1 && (
                <h3 className="mb-1.5 text-[11px] font-bold tracking-wide text-slate-400 uppercase">
                  {group.nameVi}
                </h3>
              )}
              <ul className="space-y-1.5">
                {group.items.map((food) => {
                  const on = food.id === selectedId;
                  const subgroup = foodSubgroup(food)?.nameVi;
                  const place = food.province_id ? provinceNameOf(food.province_id) : "";
                  const meta = [place, subgroup].filter(Boolean).join(" · ");
                  return (
                    <li key={food.id}>
                      <button
                        type="button"
                        data-dish-id={food.id}
                        onClick={() => onSelect(food)}
                        className={`flex w-full items-center gap-3 rounded-xl px-2 py-1.5 text-left ring-1 transition ${
                          on
                            ? "bg-brand-50 ring-brand-200"
                            : "bg-white ring-slate-100 hover:bg-slate-50 hover:ring-slate-200"
                        }`}
                      >
                        <DishThumb food={food} />
                        <span className="min-w-0 flex-1">
                          <span className="block font-bold leading-snug text-slate-900">
                            {foodDisplayName(food.name_vi)}
                          </span>
                          {meta ? (
                            <span className="mt-0.5 block truncate text-xs text-slate-500">{meta}</span>
                          ) : null}
                        </span>
                        <span className="shrink-0 text-right text-xs font-bold text-brand-700">
                          {viNum(food.calories)}
                          <span className="block font-semibold text-slate-400">kcal</span>
                        </span>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
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
  const total = [...foodsByCategory.values()].reduce((sum, items) => sum + items.length, 0);
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-extrabold tracking-tight">Tất cả quầy</h2>
        <p className="mt-2 text-sm text-slate-500">
          {total.toLocaleString("vi-VN")} thực phẩm. Bấm ảnh để xem calo, hoặc xem hết quầy.
        </p>
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
                  <h3 className="font-extrabold tracking-tight text-slate-900">{cat.name_vi}</h3>
                  <p className="mt-0.5 text-sm text-slate-500">{theme.blurb}</p>
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
          ← Tất cả quầy
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
  backLabel,
}: {
  food: Food;
  category: FoodCategory | null;
  onBack: () => void;
  backLabel?: string;
}) {
  const per100 = foodPer100g(food);
  const serving = foodServingNutrients(food);
  const sameAs100 = servingIs100g(food);
  const role = foodRoleLabel(food);
  const raw = (food.prep_state || "").toLowerCase() === "raw";
  const slug = category?.slug || "rau-cu-qua";
  const backText = backLabel || (category ? `← ${category.name_vi}` : "← Tất cả quầy");
  const servingHint = food.serving_size?.trim();

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={onBack}
          className="text-xs font-medium text-brand-600 hover:underline"
        >
          {backText}
        </button>
        {role && <span className="badge badge-gray">{role}</span>}
      </div>
      <FoodVisual food={food} slug={slug} className="mt-3 h-44 rounded-2xl sm:h-52" eager />
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
