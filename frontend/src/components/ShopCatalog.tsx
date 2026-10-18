"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { getStoredUser } from "@/lib/auth";
import {
  WIZARD_EQUIPMENT_GROUPS,
  equipmentImageFitClass,
  isWizardEquipmentSlug,
  publicEquipmentImage,
  shopSortIndex,
} from "@/lib/equipmentCatalog";
import { isShopBarKitSlug, isShopDumbbellSlug, shopProductHref } from "@/lib/shopRoutes";
import {
  EQUIPMENT_GROUP_UI,
  shopGroupForSlug,
} from "@/lib/equipmentGroupUi";
import BrandWordmark from "@/components/BrandWordmark";
import { BRAND_T_FIRST } from "@/lib/brand";
import { brandRichText } from "@/components/brandRichText";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { shopApi } from "@/lib/shopApi";
import { loadPushupDiscount } from "@/lib/fitness-tracker";
import type { ShopProduct } from "@/lib/types";
import { SITE_PAGE_MEDIA_DEFAULTS, youtubeEmbedSrc, type SitePageMedia } from "@/lib/sitePageMedia";

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


const HOW_STEPS = [
  {
    title: "Chống đẩy nhận ưu đãi giảm giá",
    description: "Càng nhiều cái, ưu đãi càng cao.",
    href: "/sukien/giam-gia",
    cta: "Thử sức",
  },
  {
    title: "Chọn dụng cụ",
    description: "Chọn món phù hợp với cách bạn muốn tập.",
    href: "/tra-cuu-don",
    cta: "Tra cứu đơn hàng",
  },
  {
    title: "Nhận tem mã",
    description: "Mỗi sản phẩm được giao kèm một mã TAPTOT.",
    href: "/batdau?nhap-ma=1",
    cta: "Nhập mã",
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
  media?: SitePageMedia;
};

export default function ShopCatalog({
  initialProduct = "",
  media = SITE_PAGE_MEDIA_DEFAULTS,
}: ShopCatalogProps) {
  const pathname = usePathname();
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
    setBusyId(product.id);
    setError("");
    try {
      if (getStoredUser()) {
        await shopApi.addToCart(product.id, 1);
        const { CART_CHANGED_EVENT } = await import("@/lib/guestCart");
        window.dispatchEvent(new CustomEvent(CART_CHANGED_EVENT));
      } else {
        const { addGuestCartItem } = await import("@/lib/guestCart");
        addGuestCartItem(product.id, 1);
      }
      setToast(`Đã thêm ${product.name_vi} vào giỏ`);
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
          isShopDumbbellSlug(product.slug) ? "grid place-items-center" : ""
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
                : isShopDumbbellSlug(product.slug)
                  ? "max-h-[62%] max-w-[48%] object-contain object-center sm:max-h-[82%] sm:max-w-[78%]"
                  : "h-full w-full object-contain p-2"
            }
          />
        ) : (
          <div className="grid h-full place-items-center text-brand-300" aria-label="Chưa có ảnh sản phẩm">
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
    stockLabel,
    outOfStock,
    priceLabel,
    pricePending,
    highlighted,
    disabled,
    busy,
    href,
    onAdd,
  }: {
    offerKey: string | number;
    products: ShopProduct[];
    href: string;
    title: string;
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
            <h3 className="font-semibold text-brand-800">
              <Link href={href} className="hover:text-brand-600">
                {title}
              </Link>
            </h3>
            <p className={`mt-0.5 text-xs font-medium ${outOfStock ? "text-brand-800" : "text-brand-600"}`}>
              {stockLabel}
            </p>
            {highlighted && (
              <p className="mt-1 text-[11px] font-bold text-brand-700">Bạn đang xem</p>
            )}
            <Link
              href={href}
              className="mt-1 inline-block text-sm font-semibold text-brand-700 hover:underline"
            >
              Xem chi tiết
            </Link>
          </div>
          <div className="flex items-center justify-between gap-3 sm:flex-col sm:items-end sm:justify-center sm:gap-2">
            <p className={`font-bold text-brand-600 ${pricePending ? "text-sm" : "text-lg"}`}>
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
    const thumbs =
      isShopBarKitSlug(product.slug)
        ? (WIZARD_EQUIPMENT_GROUPS.find((g) => g.id === "bar-and-rings")?.products || []).map((p) => ({
            ...product,
            slug: p.slug,
            name_vi: p.label_vi,
            image_url: publicEquipmentImage(p.slug),
          }))
        : [product];
    return renderOfferCard({
      offerKey: product.id,
      href: shopProductHref(product.slug),
      products: thumbs,
      title: product.name_vi,
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

  return (
    <section className="shop-brand-copy space-y-8 pb-8">
      {pushupDiscount ? (
        <div className="rounded-2xl border border-brand-200 bg-brand-50 px-5 py-4 text-sm text-brand-800">
          <p className="font-bold">
            Giảm {pushupDiscount.percent}% phụ kiện từ bài chống đẩy {pushupDiscount.reps} cái
          </p>
          <p className="mt-1 text-brand-700">
            Chi tiết hãy chọn dụng cụ tập và vào giỏ hàng để kiểm tra.
          </p>
        </div>
      ) : null}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-900 px-6 py-9 text-white shadow-soft sm:px-10 sm:py-12">
        <div className="pointer-events-none absolute -top-24 right-0 h-64 w-64 rounded-full bg-brand-500/20 blur-3xl" />
        <div className="pointer-events-none absolute -bottom-28 left-1/3 h-56 w-56 rounded-full bg-emerald-300/10 blur-3xl" />
        <div className="relative mx-auto max-w-2xl text-center">
            <h1 className="type-display flex flex-col items-center gap-1">
              <BrandWordmark snow />
              <span style={{ color: BRAND_T_FIRST }}>DỤNG CỤ</span>
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
            <h2 className="type-display text-pretty text-brand-800">
              Hướng dẫn tạo giáo án 100 ngày khi nhận dụng cụ của <BrandWordmark />
            </h2>
            <ol className="mt-6 space-y-5">
              {HOW_STEPS.map((step, index) => (
                <li key={step.title} className="flex gap-4">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-600 text-xs font-bold text-white">
                    {index + 1}
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-brand-800 sm:text-base">{step.title}</p>
                      <p className="mt-0.5 text-sm leading-relaxed text-brand-700">{brandRichText(step.description)}</p>
                    </div>
                    {"href" in step && step.href ? (
                      <Link
                        href={step.href}
                        scroll
                        className="inline-flex min-h-10 w-full shrink-0 items-center justify-center whitespace-nowrap rounded-xl bg-brand-500 px-4 py-2 text-sm font-bold text-white transition hover:bg-brand-600 sm:w-44"
                      >
                        {step.cta}
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
                src={youtubeEmbedSrc(media.shop_guide_youtube_id)}
                title="Hướng dẫn tạo giáo án 100 ngày khi nhận dụng cụ của TAPTOT"
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
            <h2 className="mt-1 type-display text-brand-800">Chọn dụng cụ phù hợp</h2>
            <p className="mt-1 text-sm text-brand-600">
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
          <div className="rounded-3xl border border-dashed border-brand-200 bg-white py-16 text-center">
            <p className="font-bold text-brand-800">Cửa hàng đang cập nhật sản phẩm</p>
            <p className="mt-1 text-sm text-brand-600">Quay lại sau để xem các dụng cụ mới.</p>
          </div>
        ) : (
          <div className="space-y-6">
            {displaySections.map((section) => (
              <div key={section.id}>
                <div className="mb-2.5 flex flex-wrap items-center gap-2">
                  <span className="badge badge-easy">{section.difficulty}</span>
                  <h3 className="font-bold text-brand-800">{section.label}</h3>
                </div>
                <div className="space-y-2.5">
                  {section.products.map((product) => renderProductRow(product))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
