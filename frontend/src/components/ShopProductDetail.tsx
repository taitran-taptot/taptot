"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { brandRichText } from "@/components/brandRichText";
import { getStoredUser } from "@/lib/auth";
import { formatVnd, mediaUrl } from "@/lib/labels";
import { renderMarkdown } from "@/lib/markdown";
import { shopApi } from "@/lib/shopApi";
import { youtubeEmbedUrl } from "@/lib/sharePlan";
import { youtubeEmbedSrc } from "@/lib/sitePageMedia";
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
  const [busy, setBusy] = useState(false);
  const [hero, setHero] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const row = await shopApi.getProductBySlug(slug);
      setProduct(row);
      setHero(row.image_url);
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

  const gallery = useMemo(() => {
    if (!product) return [];
    const urls = [product.image_url, ...(product.gallery_urls || [])].filter(
      (u, i, arr): u is string => !!u && arr.indexOf(u) === i,
    );
    return urls;
  }, [product]);

  async function addToCart() {
    if (!product) return;
    setBusy(true);
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
      setBusy(false);
    }
  }

  if (loading) {
    return <p className="py-16 text-center text-sm text-brand-600">Đang tải sản phẩm…</p>;
  }
  if (!product) {
    return (
      <div className="space-y-4 py-12 text-center">
        <p className="text-brand-700">{error || "Không tìm thấy dụng cụ này."}</p>
        <Link href="/mua-dung-cu" className="font-semibold text-brand-700 underline">
          Về cửa hàng
        </Link>
      </div>
    );
  }

  const outOfStock = product.stock_qty < 1;
  const pricePending = product.price_vnd < 1;
  const coverSrc = mediaUrl(hero || product.image_url);
  const youtubeSrc = shopYoutubeEmbed(product.youtube_url);

  return (
    <div className="shop-brand-copy space-y-8 pb-10">
      {toast ? (
        <div
          role="status"
          className="fixed top-20 right-4 z-50 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-xl"
        >
          {toast}{" "}
          <Link href="/gio-hang" className="text-brand-300 underline">
            Xem giỏ
          </Link>
        </div>
      ) : null}

      <nav className="text-sm text-brand-600">
        <Link href="/mua-dung-cu" className="font-medium text-brand-700 hover:underline">
          Dụng cụ
        </Link>
        <span className="px-2">/</span>
        <span className="text-brand-800">{product.name_vi}</span>
      </nav>

      {error ? <p className="text-sm text-brand-800">{error}</p> : null}

      <div className="grid gap-8 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-3">
          <div className="overflow-hidden rounded-3xl bg-slate-50 ring-1 ring-slate-100">
            {coverSrc ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={coverSrc} alt={product.name_vi} className="mx-auto max-h-[420px] w-full object-contain p-6" />
            ) : (
              <div className="grid aspect-[4/3] place-items-center text-brand-300">Chưa có ảnh</div>
            )}
          </div>
          {gallery.length > 1 ? (
            <div className="flex flex-wrap gap-2">
              {gallery.map((url) => {
                const src = mediaUrl(url);
                if (!src) return null;
                const active = (hero || product.image_url) === url;
                return (
                  <button
                    key={url}
                    type="button"
                    onClick={() => setHero(url)}
                    className={`h-16 w-16 overflow-hidden rounded-xl ring-2 ${
                      active ? "ring-brand-500" : "ring-slate-200"
                    }`}
                  >
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={src} alt="" className="h-full w-full object-cover" />
                  </button>
                );
              })}
            </div>
          ) : null}
        </div>

        <div className="space-y-4">
          <div>
            <p className="type-kicker text-brand-600">{brandRichText("Dụng cụ TAPTOT")}</p>
            <h1 className="mt-1 type-display text-brand-800">{product.name_vi}</h1>
          </div>
          <p className="text-2xl font-bold text-brand-600">
            {pricePending ? "Giá đang cập nhật" : formatVnd(product.price_vnd)}
          </p>
          <p className={`text-sm font-medium ${outOfStock ? "text-brand-800" : "text-brand-600"}`}>
            {outOfStock ? "Tạm hết hàng" : `Còn ${product.stock_qty} sản phẩm`}
          </p>
          <div className="flex flex-col gap-2 sm:flex-row">
            <button
              type="button"
              disabled={outOfStock || pricePending || busy}
              onClick={() => void addToCart()}
              className="inline-flex min-h-12 flex-1 items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {busy ? "Đang thêm…" : "Thêm vào giỏ"}
            </button>
            <Link
              href="/gio-hang"
              className="inline-flex min-h-12 items-center justify-center rounded-xl border border-brand-200 px-5 py-3 text-sm font-bold text-brand-700"
            >
              Giỏ hàng
            </Link>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="rounded-3xl bg-white p-6 shadow-soft sm:p-8">
          <h2 className="text-lg font-bold text-brand-800">Thông tin</h2>
          {product.description_vi ? (
            <div
              className="prose-shop mt-3 text-sm leading-relaxed text-brand-700"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(product.description_vi) }}
            />
          ) : (
            <p className="mt-3 text-sm text-brand-600">Chưa có mô tả.</p>
          )}
        </section>
        <section className="rounded-3xl bg-white p-6 shadow-soft sm:p-8">
          <h2 className="text-lg font-bold text-brand-800">Cách sử dụng</h2>
          {product.usage_vi ? (
            <div
              className="prose-shop mt-3 text-sm leading-relaxed text-brand-700"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(product.usage_vi) }}
            />
          ) : (
            <p className="mt-3 text-sm text-brand-600">Chưa có hướng dẫn.</p>
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
