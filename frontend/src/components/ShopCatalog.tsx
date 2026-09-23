"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getStoredUser } from "@/lib/auth";
import {
  WIZARD_EQUIPMENT_GROUPS,
  equipmentImageFitClass,
  isWizardEquipmentSlug,
  shopSortIndex,
} from "@/lib/equipmentCatalog";
import {
  EQUIPMENT_GROUP_UI,
  shopGroupForSlug,
} from "@/lib/equipmentGroupUi";
import BrandWordmark from "@/components/BrandWordmark";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import { loadPushupDiscount } from "@/lib/fitness-tracker";
import type { ShopProduct } from "@/lib/types";

function sortShopProducts(items: ShopProduct[]): ShopProduct[] {
  return [...items].sort((a, b) => {
    const ia = shopSortIndex(a.slug);
    const ib = shopSortIndex(b.slug);
    return ia - ib || a.slug.localeCompare(b.slug);
  });
}

function withHighlight(items: ShopProduct[], highlightSlug: string): ShopProduct[] {
  if (!highlightSlug) return items;
  return [...items].sort((a, b) => Number(b.slug === highlightSlug) - Number(a.slug === highlightSlug));
}

/** Same promo clip as the homepage equipment block. */
const EQUIPMENT_PROMO_YOUTUBE_ID = "EngW7tLk6R8";

const HOW_STEPS = [
  {
    title: "Chống đẩy nhận ưu đãi giảm giá",
    description: "Càng nhiều cái, ưu đãi càng cao.",
    href: "/sukien/giam-gia",
  },
  {
    title: "Chọn dụng cụ",
    description: "Chọn món phù hợp với cách bạn muốn tập.",
  },
  {
    title: "Nhận tem mã",
    description: "Mỗi sản phẩm được giao kèm một mã TAPTOT.",
  },
  {
    title: "Tạo lộ trình",
    description: "Quét mã để nhận lịch tập và ăn 100 ngày.",
  },
] as const;

type ShopCatalogProps = {
  initialProduct?: string;
  /** Preferred: wizard group id */
  initialGroup?: string;
  /** Legacy shop category; mapped when initialGroup empty */
  initialCategory?: string;
};

export default function ShopCatalog({
  initialProduct = "",
}: ShopCatalogProps) {
  const pathname = usePathname();
  const router = useRouter();
  const isAccount = pathname.startsWith("/tai-khoan");
  const exerciseBase = isAccount ? "/tai-khoan/bai-tap" : "/bai-tap";
  const [items, setItems] = useState<ShopProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | string | null>(null);
  const [toast, setToast] = useState("");
  const [highlightSlug] = useState(initialProduct);
  const [pushupDiscount, setPushupDiscount] = useState<ReturnType<typeof loadPushupDiscount>>(null);

  useEffect(() => {
    setPushupDiscount(loadPushupDiscount());
  }, []);

  useEffect(() => {
    shopApi
      .listProducts(1, 48)
      .then((d) =>
        setItems(sortShopProducts((d.items || []).filter((p) => isWizardEquipmentSlug(p.slug)))),
      )
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

  async function addCombo(id: string, label: string, products: ShopProduct[]) {
    if (!getStoredUser()) {
      router.push(`/dang-nhap?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setBusyId(id);
    setError("");
    try {
      for (const product of products) {
        await shopApi.addToCart(product.id, 1);
      }
      setToast(`Đã thêm combo ${label} vào giỏ`);
      setTimeout(() => setToast(""), 2500);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  function scrollToCatalog() {
    document.getElementById("danh-sach-san-pham")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  }

  const displaySections = useMemo(() => {
    return WIZARD_EQUIPMENT_GROUPS.map((g) => ({
      id: g.id,
      label: g.label_vi,
      difficulty: EQUIPMENT_GROUP_UI[g.id].difficulty,
      badge: EQUIPMENT_GROUP_UI[g.id].badge,
      products: withHighlight(
        items.filter((p) => shopGroupForSlug(p.slug) === g.id),
        highlightSlug,
      ),
    })).filter((s) => s.products.length > 0);
  }, [highlightSlug, items]);

  function productThumb(product: ShopProduct, className: string) {
    const image = mediaUrl(product.image_url);
    return (
      <div
        key={product.id}
        className={`overflow-hidden bg-slate-50 ${className} ${
          product.slug === "dumbbell" ? "grid place-items-center" : ""
        }`}
      >
        {image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={image}
            alt={product.name_vi}
            loading="lazy"
            className={
              product.slug === "gymnastic-rings"
                ? `h-full w-full ${equipmentImageFitClass(product.slug)} p-1`
                : product.slug === "dumbbell"
                  ? "max-h-[62%] max-w-[48%] object-contain object-center sm:max-h-[82%] sm:max-w-[78%]"
                  : "h-full w-full object-contain p-2"
            }
          />
        ) : (
          <div className="grid h-full place-items-center text-slate-300" aria-label="Chưa có ảnh sản phẩm">
            <svg className="h-8 w-8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.4} aria-hidden>
              <path d="M6 6h15l-1.5 9h-12zM6 6 5 3H2" />
              <circle cx="9" cy="20" r="1" />
              <circle cx="18" cy="20" r="1" />
            </svg>
          </div>
        )}
      </div>
    );
  }

  function renderOfferCard({
    offerKey,
    products,
    title,
    description,
    stockLabel,
    outOfStock,
    priceLabel,
    pricePending,
    highlighted,
    disabled,
    busy,
    onAdd,
  }: {
    offerKey: string | number;
    products: ShopProduct[];
    title: string;
    description?: string | null;
    stockLabel: string;
    outOfStock: boolean;
    priceLabel: string;
    pricePending: boolean;
    highlighted: boolean;
    disabled: boolean;
    busy: boolean;
    onAdd: () => void;
  }) {
    const thumbs = products.map((p) => p);
    return (
      <article
        key={offerKey}
        className={`overflow-hidden rounded-2xl border bg-white transition hover:border-brand-200 ${
          highlighted ? "border-brand-400 ring-2 ring-brand-100" : "border-slate-200"
        }`}
      >
        <div
          className={`grid sm:hidden ${thumbs.length > 1 ? "grid-cols-2" : "grid-cols-1"}`}
        >
          {thumbs.map((product) => productThumb(product, "aspect-[4/3]"))}
        </div>
        <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-4 sm:p-3">
          <div className={`hidden shrink-0 sm:flex ${thumbs.length > 1 ? "gap-1" : ""}`}>
            {thumbs.map((product) =>
              productThumb(
                product,
                thumbs.length > 1
                  ? "h-[88px] w-[72px] rounded-xl"
                  : "h-[88px] w-[88px] rounded-xl",
              ),
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-slate-900">{title}</h3>
            {description ? (
              <p className="mt-0.5 line-clamp-2 text-sm leading-relaxed text-slate-500">{description}</p>
            ) : null}
            <p className={`mt-0.5 text-xs font-medium ${outOfStock ? "text-amber-700" : "text-emerald-700"}`}>
              {stockLabel}
            </p>
            {highlighted && (
              <p className="mt-1 text-[11px] font-bold text-brand-700">Bạn đang xem</p>
            )}
          </div>
          <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-center sm:gap-2">
            <p className={`font-bold ${pricePending ? "text-sm text-slate-500" : "text-lg text-brand-700"}`}>
              {pricePending ? "Giá đang cập nhật" : priceLabel}
            </p>
            <button
              type="button"
              disabled={disabled}
              onClick={onAdd}
              className="min-h-11 flex-1 rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 sm:min-h-10 sm:flex-none"
            >
              {outOfStock
                ? "Tạm hết hàng"
                : pricePending
                  ? "Chưa mở bán"
                  : busy
                    ? "Đang thêm…"
                    : "Thêm vào giỏ"}
            </button>
          </div>
        </div>
      </article>
    );
  }

  function renderProductRow(product: ShopProduct) {
    const outOfStock = product.stock_qty < 1;
    const pricePending = product.price_vnd < 1;
    return renderOfferCard({
      offerKey: product.id,
      products: [product],
      title: product.name_vi,
      description: product.description_vi,
      stockLabel: outOfStock ? "Tạm hết hàng" : `Còn ${product.stock_qty} sản phẩm`,
      outOfStock,
      priceLabel: formatVnd(product.price_vnd),
      pricePending,
      highlighted: product.slug === highlightSlug,
      disabled: outOfStock || pricePending || busyId === product.id,
      busy: busyId === product.id,
      onAdd: () => void add(product),
    });
  }

  function renderComboRow(section: (typeof displaySections)[number]) {
    const { products } = section;
    const comboId = `combo-${section.id}`;
    const pricePending = products.some((p) => p.price_vnd < 1);
    const outOfStock = products.some((p) => p.stock_qty < 1);
    const total = products.reduce((sum, p) => sum + p.price_vnd, 0);
    const stock = Math.min(...products.map((p) => p.stock_qty));
    const description =
      products
        .map((p) => p.description_vi?.trim())
        .filter(Boolean)
        .join(" ") || products.map((p) => p.name_vi).join(" và ");
    return renderOfferCard({
      offerKey: comboId,
      products,
      title: `Combo ${section.label}`,
      description,
      stockLabel: outOfStock ? "Tạm hết hàng" : `Còn ${stock} bộ`,
      outOfStock,
      priceLabel: formatVnd(total),
      pricePending,
      highlighted: products.some((p) => p.slug === highlightSlug),
      disabled: outOfStock || pricePending || busyId === comboId,
      busy: busyId === comboId,
      onAdd: () => void addCombo(comboId, section.label, products),
    });
  }

  return (
    <section className="space-y-8 pb-8">
      {pushupDiscount ? (
        <div className="rounded-2xl border border-orange-200 bg-orange-50 px-5 py-4 text-sm text-orange-950">
          <p className="font-bold">
            Giảm {pushupDiscount.percent}% phụ kiện từ bài chống đẩy {pushupDiscount.reps} cái
          </p>
          <p className="mt-1 text-orange-800">
            Mức này đang lưu trên máy bạn. Thanh toán chưa tự trừ — đưa phiếu / xác nhận với TAPTOT khi nhận đơn.
          </p>
        </div>
      ) : null}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900 px-6 py-9 text-white shadow-soft sm:px-10 sm:py-12">
        <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="relative mx-auto max-w-2xl text-center">
            <h1 className="type-display flex flex-col items-center gap-1">
              <BrandWordmark snow />
              <span>DỤNG CỤ</span>
            </h1>
            <div className="mt-6 flex flex-col items-stretch justify-center gap-2.5 sm:flex-row sm:items-center sm:gap-3">
              <button
                type="button"
                onClick={scrollToCatalog}
                className="inline-flex min-h-11 items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-400 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
              >
                Chọn dụng cụ
              </button>
              <Link
                href={exerciseBase}
                className="inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-bold text-white transition hover:bg-white/15"
              >
                Xem kho bài tập
              </Link>
            </div>
          </div>
      </div>

      <section className="relative overflow-hidden rounded-[2rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-8 shadow-soft sm:px-10 sm:py-10">
        <div
          className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
          aria-hidden
        />
        <div className="relative grid items-center gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12">
          <div>
            <h2 className="type-display text-pretty text-slate-900">
              Hướng dẫn tạo lịch khi nhận dụng cụ của <BrandWordmark />
            </h2>
            <ol className="mt-6 space-y-5">
              {HOW_STEPS.map((step, index) => (
                <li key={step.title} className="flex gap-4">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">
                    {index + 1}
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-slate-900 sm:text-base">{step.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-slate-500">{step.description}</p>
                    </div>
                    {"href" in step && step.href ? (
                      <Link
                        href={step.href}
                        className="inline-flex min-h-10 shrink-0 items-center justify-center rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-600"
                      >
                        Thử sức
                      </Link>
                    ) : null}
                  </div>
                </li>
              ))}
            </ol>
          </div>
          <div className="overflow-hidden rounded-2xl border border-brand-100 bg-white/90 shadow-sm">
            <div className="relative aspect-video w-full bg-slate-900">
              <iframe
                className="absolute inset-0 h-full w-full"
                src={`https://www.youtube-nocookie.com/embed/${EQUIPMENT_PROMO_YOUTUBE_ID}`}
                title="Hướng dẫn tạo lịch khi nhận dụng cụ của TAPTOT"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                loading="lazy"
                referrerPolicy="strict-origin-when-cross-origin"
              />
            </div>
          </div>
        </div>
      </section>

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
        <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
          <div>
            <p className="type-kicker text-brand-600">Cửa hàng</p>
            <h2 className="mt-1 type-display text-slate-900">Chọn dụng cụ phù hợp</h2>
            <p className="mt-1 text-sm text-slate-500">
              {loading ? "Đang tải sản phẩm…" : `${displaySections.length} lựa chọn`}
            </p>
          </div>
          <Link
            href="/gio-hang"
            className="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-xl border border-brand-200 bg-brand-50 px-4 py-2.5 text-sm font-bold text-brand-700 transition hover:bg-brand-100 sm:w-auto"
          >
            <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
              <path d="M6 6h15l-1.5 9h-12zM6 6 5 3H2" />
              <circle cx="9" cy="20" r="1" />
              <circle cx="18" cy="20" r="1" />
            </svg>
            Xem giỏ hàng
          </Link>
        </div>

        {error && (
          <div role="alert" className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
            Không tải được cửa hàng: {error}
          </div>
        )}

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 rounded-2xl border border-slate-100 bg-white p-3">
                <div className="h-[88px] w-[88px] animate-pulse rounded-xl bg-slate-100" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 w-1/3 animate-pulse rounded bg-slate-100" />
                  <div className="h-3 w-1/4 animate-pulse rounded bg-slate-100" />
                </div>
              </div>
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="rounded-3xl border border-dashed border-slate-300 bg-white py-16 text-center">
            <p className="font-bold text-slate-700">Cửa hàng đang cập nhật sản phẩm</p>
            <p className="mt-1 text-sm text-slate-500">Quay lại sau để xem các dụng cụ mới.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {displaySections.map((section) => (
              <div key={section.id}>
                <div className="mb-2.5 flex flex-wrap items-center gap-2">
                  <span className={`badge ${section.badge}`}>{section.difficulty}</span>
                  <h3 className="font-bold text-slate-900">{section.label}</h3>
                </div>
                <div className="space-y-2.5">
                  {section.products.length > 1
                    ? renderComboRow(section)
                    : section.products.map((product) => renderProductRow(product))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
