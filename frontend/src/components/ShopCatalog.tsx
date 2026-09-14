"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getStoredUser } from "@/lib/auth";
import { WIZARD_EQUIPMENT_GROUPS, equipmentImageFitClass, shopSortIndex } from "@/lib/equipmentCatalog";
import {
  EQUIPMENT_GROUP_UI,
  resolveShopGroupFilter,
  shopDifficultyLabel,
  shopGroupForSlug,
  type ShopEquipmentGroupFilter,
} from "@/lib/equipmentGroupUi";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import type { ShopProduct } from "@/lib/types";

type Availability = "all" | "available";
type SortKey = "featured" | "price-asc" | "price-desc";

function sortShopProducts(items: ShopProduct[]): ShopProduct[] {
  return [...items].sort((a, b) => {
    const ia = shopSortIndex(a.slug);
    const ib = shopSortIndex(b.slug);
    return ia - ib || a.slug.localeCompare(b.slug);
  });
}

function applySort(items: ShopProduct[], sort: SortKey, highlightSlug: string): ShopProduct[] {
  let next = items;
  if (sort === "price-asc") next = [...items].sort((a, b) => a.price_vnd - b.price_vnd);
  else if (sort === "price-desc") next = [...items].sort((a, b) => b.price_vnd - a.price_vnd);
  if (!highlightSlug) return next;
  return [...next].sort((a, b) => Number(b.slug === highlightSlug) - Number(a.slug === highlightSlug));
}

type ShopCatalogProps = {
  initialProduct?: string;
  /** Preferred: wizard group id */
  initialGroup?: string;
  /** Legacy shop category; mapped when initialGroup empty */
  initialCategory?: string;
  /** Arrived from a page that introduced the included 100-day plan. */
  highlightGiftOffer?: boolean;
};

export default function ShopCatalog({
  initialProduct = "",
  initialGroup = "",
  initialCategory = "",
  highlightGiftOffer = false,
}: ShopCatalogProps) {
  const pathname = usePathname();
  const router = useRouter();
  const isAccount = pathname.startsWith("/tai-khoan");
  const exerciseBase = isAccount ? "/tai-khoan/bai-tap" : "/bai-tap";
  const equipmentBase = isAccount ? "/tai-khoan/dung-cu" : "/dung-cu";
  const [items, setItems] = useState<ShopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [toast, setToast] = useState("");
  const [query, setQuery] = useState("");
  const [group, setGroup] = useState<ShopEquipmentGroupFilter>(() =>
    resolveShopGroupFilter(initialGroup, initialCategory),
  );
  const [availability, setAvailability] = useState<Availability>("all");
  const [sort, setSort] = useState<SortKey>("featured");
  const [highlightSlug] = useState(initialProduct);

  useEffect(() => {
    shopApi
      .listProducts(1, 48)
      .then((d) => setItems(sortShopProducts(d.items || [])))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  async function add(product: ShopProduct) {
    if (!getStoredUser()) {
      router.push(`/dang-nhap?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setBusyId(product.id);
    setError("");
    try {
      await shopApi.addToCart(product.id, 1);
      setToast(`Đã thêm ${product.name_vi} vào giỏ`);
      setTimeout(() => setToast(""), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  const filteredBase = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase("vi");
    return items.filter((product) => {
      const matchesQuery =
        !normalizedQuery ||
        `${product.name_vi} ${product.description_vi || ""} ${product.slug}`
          .toLocaleLowerCase("vi")
          .includes(normalizedQuery);
      const productGroup = shopGroupForSlug(product.slug);
      const matchesGroup = group === "all" || productGroup === group;
      const matchesAvailability = availability === "all" || product.stock_qty > 0;
      return matchesQuery && matchesGroup && matchesAvailability;
    });
  }, [availability, group, items, query]);

  const visibleItems = useMemo(
    () => applySort(filteredBase, sort, highlightSlug),
    [filteredBase, highlightSlug, sort],
  );

  const sections = useMemo(() => {
    if (group !== "all") return null;
    const byGroup = WIZARD_EQUIPMENT_GROUPS.map((g) => ({
      id: g.id,
      label: g.label_vi,
      difficulty: EQUIPMENT_GROUP_UI[g.id].difficulty,
      badge: EQUIPMENT_GROUP_UI[g.id].badge,
      products: applySort(
        filteredBase.filter((p) => shopGroupForSlug(p.slug) === g.id),
        sort,
        highlightSlug,
      ),
    })).filter((s) => s.products.length > 0);

    const other = applySort(
      filteredBase.filter((p) => shopGroupForSlug(p.slug) === "other"),
      sort,
      highlightSlug,
    );

    return { byGroup, other };
  }, [filteredBase, group, highlightSlug, sort]);

  const hasActiveFilters = query.trim() || group !== "all" || availability !== "all";

  function resetFilters() {
    setQuery("");
    setGroup("all");
    setAvailability("all");
    setSort("featured");
  }

  function renderProductCard(product: ShopProduct) {
    const image = mediaUrl(product.image_url);
    const outOfStock = product.stock_qty < 1;
    const pricePending = product.price_vnd < 1;
    const highlighted = product.slug === highlightSlug;
    const disabled = outOfStock || pricePending || busyId === product.id;
    const diff = shopDifficultyLabel(product.slug);

    return (
      <article
        key={product.id}
        className={`group flex flex-col overflow-hidden rounded-2xl border bg-white transition hover:-translate-y-0.5 hover:shadow-lg ${
          highlighted ? "border-brand-400 ring-2 ring-brand-100" : "border-slate-200"
        }`}
      >
        <div className="relative aspect-[4/3] overflow-hidden bg-slate-50">
          {image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={image}
              alt={product.name_vi}
              loading="lazy"
              className={`h-full w-full transition duration-300 group-hover:scale-[1.03] ${
                product.slug === "gymnastic-rings"
                  ? `${equipmentImageFitClass(product.slug)} p-1`
                  : "object-contain p-4"
              }`}
            />
          ) : (
            <div className="grid h-full place-items-center text-slate-300" aria-label="Chưa có ảnh sản phẩm">
              <svg className="h-16 w-16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} aria-hidden>
                <path d="M6 6h15l-1.5 9h-12zM6 6 5 3H2" />
                <circle cx="9" cy="20" r="1" />
                <circle cx="18" cy="20" r="1" />
              </svg>
            </div>
          )}
          <div className="absolute top-3 left-3 flex flex-wrap gap-2">
            <span className={`badge ${diff.badge} shadow-sm`}>{diff.vi}</span>
            <span className="rounded-full bg-white px-2.5 py-1 text-[11px] font-bold text-brand-700 shadow-sm ring-1 ring-brand-100">
              Kèm lộ trình 100 ngày
            </span>
            {highlighted && (
              <span className="rounded-full bg-brand-500 px-2.5 py-1 text-[11px] font-bold text-white shadow-sm">
                Bạn đang xem
              </span>
            )}
          </div>
        </div>

        <div className="flex flex-1 flex-col p-5">
          <h3 className="text-lg font-extrabold tracking-tight text-slate-900">{product.name_vi}</h3>
          <p className="mt-2 line-clamp-2 min-h-10 text-sm leading-relaxed text-slate-500">
            {product.description_vi || "Dụng cụ hỗ trợ đa dạng bài tập trong kho TAPTOT."}
          </p>
          <div className="mt-4 flex items-end justify-between gap-3">
            <div>
              <p className={`font-extrabold ${pricePending ? "text-sm text-slate-500" : "text-xl text-brand-700"}`}>
                {pricePending ? "Giá đang cập nhật" : formatVnd(product.price_vnd)}
              </p>
              <p className={`mt-0.5 text-xs font-medium ${outOfStock ? "text-amber-700" : "text-emerald-700"}`}>
                {outOfStock ? "Tạm hết hàng" : `Còn ${product.stock_qty} sản phẩm`}
              </p>
            </div>
            {!outOfStock && !pricePending && (
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-[11px] font-bold text-emerald-700">
                Sẵn hàng
              </span>
            )}
          </div>

          <div className="mt-5 grid gap-2">
            <button
              type="button"
              disabled={disabled}
              onClick={() => void add(product)}
              className="min-h-11 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {outOfStock
                ? "Tạm hết hàng"
                : pricePending
                  ? "Chưa mở bán"
                  : busyId === product.id
                    ? "Đang thêm…"
                    : "Thêm vào giỏ · Có quà tặng"}
            </button>
            <Link
              href={`${exerciseBase}?equipment=${encodeURIComponent(product.slug)}`}
              className="inline-flex min-h-10 items-center justify-center text-sm font-bold text-slate-600 transition hover:text-brand-700"
            >
              Xem bài tập với dụng cụ này
              <span className="ml-1.5" aria-hidden>
                →
              </span>
            </Link>
          </div>
        </div>
      </article>
    );
  }

  function renderGrid(products: ShopProduct[]) {
    return (
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {products.map((product) => renderProductCard(product))}
      </div>
    );
  }

  return (
    <section className="space-y-8 pb-8">
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900 px-6 py-9 text-white shadow-soft sm:px-10 sm:py-12">
        <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="relative grid items-center gap-8 md:grid-cols-[minmax(0,1fr)_20rem]">
          <div className="max-w-2xl">
            <p className="text-xs font-bold tracking-[0.2em] text-brand-300 uppercase">
              TAPTOT Equipment
            </p>
            <h1 className="mt-3 text-3xl font-extrabold tracking-tight sm:text-4xl">
              Chọn dụng cụ để bắt đầu — lộ trình 100 ngày TAPTOT tặng bạn
            </h1>
            <p className="mt-4 max-w-xl text-sm leading-relaxed text-slate-300 sm:text-base">
              Mỗi sản phẩm đi kèm một mã trên tem. Khi nhận hàng, bạn chỉ cần quét mã để tạo lịch tập và lịch ăn theo thể trạng của mình.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <a
                href="#danh-sach-san-pham"
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                Chọn dụng cụ
              </a>
              <Link
                href={equipmentBase}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:bg-white/15"
              >
                Xem kho hướng dẫn
              </Link>
            </div>
          </div>
          <div className="hidden rounded-3xl border border-white/10 bg-white/5 p-6 backdrop-blur md:block">
            <div className="space-y-2.5">
              {WIZARD_EQUIPMENT_GROUPS.map((g) => {
                const ui = EQUIPMENT_GROUP_UI[g.id];
                return (
                  <div
                    key={g.id}
                    className="flex items-center gap-3 rounded-xl border border-white/10 bg-white/5 px-3 py-2.5"
                  >
                    <span className={`badge ${ui.badge}`}>{ui.difficulty}</span>
                    <span className="text-sm font-semibold text-white">{g.label_vi}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-4 text-center text-xs leading-relaxed text-slate-400">
              Cùng 3 nhóm độ khó như khi tạo lịch tập.
            </p>
          </div>
        </div>
      </div>

      <div
        role={highlightGiftOffer ? "status" : undefined}
        className={`rounded-2xl border border-brand-200 bg-brand-50 px-5 py-4 sm:flex sm:items-center sm:justify-between sm:gap-6 ${
          highlightGiftOffer ? "shadow-[0_16px_38px_-28px_rgba(22,163,74,0.65)]" : ""
        }`}
      >
        <div>
          <p className="font-extrabold text-brand-900">Lộ trình 100 ngày được tặng cùng dụng cụ</p>
          <p className="mt-1 text-sm leading-relaxed text-brand-800/80">
            Mã dùng một lần nằm trên tem sản phẩm. Nhận hàng, quét mã và tạo lịch tập cùng lịch ăn của bạn.
          </p>
        </div>
        <span className="mt-3 inline-flex shrink-0 rounded-full bg-white px-3 py-1.5 text-xs font-bold text-brand-700 ring-1 ring-brand-200 sm:mt-0">
          1 sản phẩm · 1 mã trên tem
        </span>
      </div>

      <div className="grid overflow-hidden rounded-2xl border border-slate-200 bg-white sm:grid-cols-3">
        {[
          ["Chọn dụng cụ", "Chọn món phù hợp với cách bạn muốn tập."],
          ["Nhận tem mã", "Mỗi sản phẩm được giao kèm một mã TAPTOT."],
          ["Tạo lộ trình", "Quét mã để nhận lịch tập và ăn 100 ngày."],
        ].map(([title, description], index) => (
          <div
            key={title}
            className={`flex gap-3 px-5 py-4 ${index > 0 ? "border-t border-slate-100 sm:border-t-0 sm:border-l" : ""}`}
          >
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-brand-50 text-sm font-extrabold text-brand-700">
              {index + 1}
            </span>
            <div>
              <p className="text-sm font-bold text-slate-900">{title}</p>
              <p className="mt-0.5 text-xs leading-relaxed text-slate-500">{description}</p>
            </div>
          </div>
        ))}
      </div>

      {toast && (
        <div
          role="status"
          className="fixed top-20 right-4 z-50 flex items-center gap-3 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-xl"
        >
          <span className="grid h-6 w-6 place-items-center rounded-full bg-brand-500" aria-hidden>
            ✓
          </span>
          {toast}
          <Link href="/gio-hang" className="text-brand-300 underline underline-offset-4">
            Xem giỏ
          </Link>
        </div>
      )}

      <div id="danh-sach-san-pham" className="scroll-mt-24">
        <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-bold tracking-widest text-brand-600 uppercase">Cửa hàng</p>
            <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900">
              Chọn dụng cụ phù hợp
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {loading ? "Đang tải sản phẩm…" : `${visibleItems.length} sản phẩm phù hợp`}
            </p>
          </div>
          <Link
            href="/gio-hang"
            className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-700 transition hover:bg-brand-100"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path d="M6 6h15l-1.5 9h-12zM6 6 5 3H2" />
              <circle cx="9" cy="20" r="1" />
              <circle cx="18" cy="20" r="1" />
            </svg>
            Xem giỏ hàng
          </Link>
        </div>

        <div className="mb-5 rounded-2xl border border-slate-200 bg-white p-3 shadow-sm sm:p-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto_auto]">
            <label className="relative block">
              <span className="sr-only">Tìm sản phẩm</span>
              <svg
                className="pointer-events-none absolute top-1/2 left-3.5 h-4 w-4 -translate-y-1/2 text-slate-400"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden
              >
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-4-4" />
              </svg>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                type="search"
                placeholder="Tìm xà, tạ, dây kháng lực…"
                className="field min-h-11 pl-10 text-sm"
              />
            </label>
            <label>
              <span className="sr-only">Tình trạng hàng</span>
              <select
                value={availability}
                onChange={(event) => setAvailability(event.target.value as Availability)}
                className="field min-h-11 min-w-40 text-sm"
              >
                <option value="all">Mọi tình trạng</option>
                <option value="available">Còn hàng</option>
              </select>
            </label>
            <label>
              <span className="sr-only">Sắp xếp sản phẩm</span>
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value as SortKey)}
                className="field min-h-11 min-w-44 text-sm"
              >
                <option value="featured">TAPTOT đề xuất</option>
                <option value="price-asc">Giá thấp đến cao</option>
                <option value="price-desc">Giá cao đến thấp</option>
              </select>
            </label>
          </div>
          <div className="mt-3 flex gap-2 overflow-x-auto pb-1">
            <button
              type="button"
              onClick={() => setGroup("all")}
              aria-pressed={group === "all"}
              className={`min-h-10 shrink-0 rounded-full px-4 text-sm font-semibold transition ${
                group === "all"
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700"
              }`}
            >
              Tất cả
            </button>
            {WIZARD_EQUIPMENT_GROUPS.map((g) => {
              const ui = EQUIPMENT_GROUP_UI[g.id];
              const on = group === g.id;
              return (
                <button
                  key={g.id}
                  type="button"
                  onClick={() => setGroup(g.id)}
                  aria-pressed={on}
                  className={`inline-flex min-h-10 shrink-0 items-center gap-2 rounded-full px-4 text-sm font-semibold transition ${
                    on
                      ? "bg-slate-900 text-white"
                      : "bg-slate-100 text-slate-600 hover:bg-brand-50 hover:text-brand-700"
                  }`}
                >
                  <span className={`badge ${ui.badge} ${on ? "ring-1 ring-white/40" : ""}`}>
                    {ui.difficulty}
                  </span>
                  {g.label_vi}
                </button>
              );
            })}
          </div>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            Không tải được cửa hàng: {error}
          </div>
        )}

        {loading ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="overflow-hidden rounded-2xl border border-slate-100 bg-white">
                <div className="aspect-[4/3] animate-pulse bg-slate-100" />
                <div className="space-y-3 p-5">
                  <div className="h-4 w-2/3 animate-pulse rounded bg-slate-100" />
                  <div className="h-3 w-full animate-pulse rounded bg-slate-100" />
                  <div className="h-10 animate-pulse rounded-xl bg-slate-100" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white py-16 text-center">
            <p className="font-bold text-slate-700">Cửa hàng đang cập nhật sản phẩm</p>
            <p className="mt-1 text-sm text-slate-500">Quay lại sau để xem các dụng cụ mới.</p>
          </div>
        ) : visibleItems.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white px-5 py-16 text-center">
            <p className="font-bold text-slate-700">Không tìm thấy sản phẩm phù hợp</p>
            <p className="mt-1 text-sm text-slate-500">Thử từ khóa khác hoặc bỏ bớt bộ lọc.</p>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={resetFilters}
                className="mt-5 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-bold text-white hover:bg-slate-700"
              >
                Xóa bộ lọc
              </button>
            )}
          </div>
        ) : group === "all" && sections ? (
          <div className="space-y-10">
            {sections.byGroup.map((section) => (
              <div key={section.id}>
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <span className={`badge ${section.badge}`}>{section.difficulty}</span>
                  <h3 className="text-lg font-extrabold text-slate-900">{section.label}</h3>
                  <span className="text-sm text-slate-400">{section.products.length} sản phẩm</span>
                </div>
                {renderGrid(section.products)}
              </div>
            ))}
            {sections.other.length > 0 && (
              <div>
                <div className="mb-4 flex flex-wrap items-center gap-2">
                  <span className="badge badge-mid">Khác</span>
                  <h3 className="text-lg font-extrabold text-slate-900">Dụng cụ khác</h3>
                  <span className="text-sm text-slate-400">{sections.other.length} sản phẩm</span>
                </div>
                {renderGrid(sections.other)}
              </div>
            )}
          </div>
        ) : (
          renderGrid(visibleItems)
        )}
      </div>

      <div className="rounded-3xl bg-brand-50 px-6 py-8 ring-1 ring-brand-100 sm:flex sm:items-center sm:justify-between sm:gap-8 sm:px-8">
        <div>
          <p className="text-lg font-extrabold text-slate-900">Chưa biết nên bắt đầu với dụng cụ nào?</p>
          <p className="mt-1 text-sm leading-relaxed text-slate-600">
            Bắt đầu từ nhóm Dễ (dây kháng lực), rồi tăng dần khi đã quen nhịp tập.
          </p>
        </div>
        <Link
          href={equipmentBase}
          className="mt-5 inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl bg-slate-900 px-5 py-3 text-sm font-bold text-white transition hover:bg-slate-700 sm:mt-0"
        >
          Khám phá kho dụng cụ
        </Link>
      </div>
    </section>
  );
}
