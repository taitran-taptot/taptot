"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { brandRichText } from "@/components/brandRichText";
import ProductDetailGallery from "@/components/ProductDetailGallery";
import CartAddedToast from "@/components/CartAddedToast";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { renderMarkdown } from "@/lib/markdown";
import { addShopLine, shopApi } from "@/lib/shopApi";
import { youtubeEmbedUrl } from "@/lib/sharePlan";
import { youtubeEmbedSrc } from "@/lib/sitePageMedia";
import { loadPushupDiscount, priceAfterDiscount } from "@/lib/fitness-tracker";
import type { ShopProduct } from "@/lib/types";

function shopYoutubeEmbed(url: string | null | undefined): string | null {
  const raw = (url || "").trim();
  if (!raw) return null;
  if (/^[\w-]{6,}$/.test(raw)) return youtubeEmbedSrc(raw);
  const embed = youtubeEmbedUrl(raw);
  if (!embed) return null;
  const id = embed.split("/embed/")[1]?.split("?")[0];
  return id ? youtubeEmbedSrc(id) : null;
}

export default function ShopProductDetail({ slug }: { slug: string }) {
  const [product, setProduct] = useState<ShopProduct | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [toast, setToast] = useState("");
  const [added, setAdded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [discountPercent, setDiscountPercent] = useState(0);

  useEffect(() => {
    const saved = loadPushupDiscount();
    setDiscountPercent(saved && saved.percent > 0 ? saved.percent : 0);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const row = await shopApi.getProductBySlug(slug);
      setProduct(row);
    } catch (e) {
      setError((e as Error).message || "Không tìm thấy sản phẩm");
      setProduct(null);
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    void load();
  }, [load]);

  async function addToCart() {
    if (!product) return;
    setBusy(true);
    setError("");
    try {
      await addShopLine(product.id, product.stock_qty);
      setAdded(true);
      setToast(`Đã thêm ${product.name_vi} vào giỏ`);
      window.setTimeout(() => {
        setToast("");
        setAdded(false);
      }, 4000);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="py-16 text-center text-sm text-slate-700">Đang tải sản phẩm…</p>;
  }
  if (!product) {
    return (
      <div className="space-y-4 py-12 text-center">
        <p className="text-slate-900">{error || "Không tìm thấy dụng cụ này."}</p>
        <Link href="/mua-dung-cu" className="font-semibold text-slate-900 underline">
          Về cửa hàng
        </Link>
      </div>
    );
  }

  const outOfStock = product.stock_qty < 1;
  const pricePending = product.price_vnd < 1;
  const coverSrc = mediaUrl(product.image_url);
  const detailPhotos = (product.gallery_urls || []).filter((url): url is string => Boolean(url && url.trim()));
  const youtubeSrc = shopYoutubeEmbed(product.youtube_url);

  return (
    <div className="shop-brand-copy space-y-8 pb-10">
      <CartAddedToast message={toast} />

      <nav className="text-sm text-slate-700">
        <Link href="/mua-dung-cu" className="font-medium text-slate-900 hover:underline">
          Dụng cụ
        </Link>
        <span className="px-2">/</span>
        <span className="text-slate-900">{product.name_vi}</span>
      </nav>

      {error ? <p className="text-sm text-slate-900">{error}</p> : null}

      <div className="grid items-center gap-8 lg:grid-cols-2">
        <div className="overflow-hidden rounded-3xl bg-slate-50 ring-1 ring-slate-100">
          {coverSrc ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={coverSrc} alt={product.name_vi} className="mx-auto max-h-[420px] w-full object-contain p-6" />
          ) : (
            <div className="grid aspect-[4/3] place-items-center text-slate-400">Chưa có ảnh</div>
          )}
        </div>

        <div className="space-y-4 text-center">
          <div>
            <p className="type-kicker text-slate-700">{brandRichText("Dụng cụ TAPTOT")}</p>
            <h1 className="mt-1 type-display text-slate-900">{product.name_vi}</h1>
          </div>
          <p className="text-2xl font-bold text-slate-900">
            {pricePending ? (
              "Giá đang cập nhật"
            ) : discountPercent > 0 ? (
              <span className="inline-flex flex-wrap items-baseline justify-center gap-2">
                <span className="text-base font-medium text-slate-400 line-through">
                  {formatVnd(product.price_vnd)}
                </span>
                <span>{formatVnd(priceAfterDiscount(product.price_vnd, discountPercent))}</span>
              </span>
            ) : (
              formatVnd(product.price_vnd)
            )}
          </p>
          <p className={`text-sm font-medium ${outOfStock ? "text-slate-900" : "text-slate-700"}`}>
            {outOfStock ? "Tạm hết hàng" : `Còn ${product.stock_qty} sản phẩm`}
          </p>
          <div className="flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
            <button
              type="button"
              disabled={outOfStock || pricePending || busy}
              onClick={() => void addToCart()}
              className="inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500 sm:w-44"
            >
              {busy ? "Đang thêm…" : added ? "Đã thêm" : "Thêm vào giỏ"}
            </button>
            <Link
              href="/gio-hang"
              className="inline-flex min-h-12 w-full items-center justify-center rounded-xl border border-slate-300 px-5 py-3 text-sm font-bold text-slate-900 sm:w-44"
            >
              Giỏ hàng
            </Link>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2 lg:items-stretch">
        <section className="h-full rounded-3xl bg-white p-6 shadow-soft sm:p-8">
          <h2 className="text-lg font-bold text-slate-900">Thông tin</h2>
          {product.description_vi ? (
            <div
              className="prose-shop mt-3 text-sm leading-relaxed text-slate-900"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(product.description_vi) }}
            />
          ) : (
            <p className="mt-3 text-sm text-slate-700">Chưa có mô tả.</p>
          )}
          <ProductDetailGallery urls={detailPhotos} name={product.name_vi} />
        </section>
        <section className="h-full rounded-3xl bg-white p-6 shadow-soft sm:p-8">
          <h2 className="text-lg font-bold text-slate-900">Cách sử dụng</h2>
          {product.usage_vi ? (
            <div
              className="prose-shop mt-3 text-sm leading-relaxed text-slate-900"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(product.usage_vi) }}
            />
          ) : (
            <p className="mt-3 text-sm text-slate-700">Chưa có hướng dẫn.</p>
          )}
          {youtubeSrc ? (
            <div className="relative mt-5 aspect-video overflow-hidden rounded-2xl bg-slate-900">
              <iframe
                className="absolute inset-0 h-full w-full"
                src={youtubeSrc}
                title={`Video hướng dẫn ${product.name_vi}`}
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                allowFullScreen
                loading="lazy"
                referrerPolicy="strict-origin-when-cross-origin"
              />
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}
