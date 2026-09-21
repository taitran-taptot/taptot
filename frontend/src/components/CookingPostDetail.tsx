"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { mediaUrl } from "@/lib/labels";
import { renderMarkdown } from "@/lib/markdown";
import { FOODS_HREF } from "@/lib/foodRoutes";
import type { CookingIngredient, CookingPost } from "@/lib/types";
import FoodBrowseTabs from "./FoodBrowseTabs";

function yieldLabel(post: CookingPost): string | null {
  const servings = post.servings || 0;
  const total = post.yield_grams;
  const each = post.grams_per_serving;
  if (!servings && !total) return null;
  const bits: string[] = [];
  if (servings) bits.push(`${servings} người`);
  if (total) bits.push(`~${Math.round(total)} g thành phẩm`);
  if (each) bits.push(`~${Math.round(each)} g/suất`);
  return bits.join(" · ");
}

function IngredientCard({ item }: { item: CookingIngredient }) {
  const src = mediaUrl(item.image_url);
  const name = item.name_vi || item.food_slug || "Nguyên liệu";
  const href = item.food_slug ? `${FOODS_HREF}?q=${encodeURIComponent(name)}` : FOODS_HREF;
  return (
    <Link
      href={href}
      className="flex gap-3 overflow-hidden rounded-xl bg-slate-50 ring-1 ring-slate-100 transition hover:ring-brand-200"
    >
      <span className="h-20 w-20 shrink-0 bg-slate-100">
        {src ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={src} alt={name} className="h-full w-full object-cover" />
        ) : (
          <span className="grid h-full place-items-center text-xl text-slate-300">🥬</span>
        )}
      </span>
      <span className="min-w-0 flex-1 py-2 pr-3">
        <span className="block font-bold leading-snug text-slate-900">{name}</span>
        <span className="mt-0.5 block text-sm font-semibold text-brand-700">
          {item.amount_label || (item.grams != null ? `${item.grams}g` : "")}
        </span>
        {item.note ? <span className="mt-0.5 block text-xs text-slate-500">{item.note}</span> : null}
      </span>
    </Link>
  );
}

export default function CookingPostDetail({
  slug,
  listHref = "/cach-nau",
}: {
  slug: string;
  listHref?: string;
}) {
  const [post, setPost] = useState<CookingPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    cookingPostsApi
      .getBySlug(slug)
      .then(setPost)
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div>
        <FoodBrowseTabs />
        <div className="h-64 animate-pulse rounded-2xl bg-white shadow-soft" />
      </div>
    );
  }
  if (error || !post) {
    return (
      <div>
        <FoodBrowseTabs />
        <div className="py-16 text-center">
          <p className="text-rose-500">{error || "Không tìm thấy bài viết"}</p>
          <Link href={listHref} className="mt-4 inline-block text-sm font-semibold text-brand-600">
            ← Tất cả bài nấu ăn
          </Link>
        </div>
      </div>
    );
  }

  const cover = mediaUrl(post.cover_image_url);
  const yieldText = yieldLabel(post);
  const ingredients = post.ingredients || [];

  return (
    <div>
      <FoodBrowseTabs />
      <article className="mx-auto max-w-3xl">
        <Link href={listHref} className="text-sm font-semibold text-brand-600 hover:text-brand-700">
          ← Cách nấu món ăn ngon
        </Link>
        <h1 className="mt-4 type-display">{post.title_vi}</h1>
        {post.excerpt && <p className="mt-2 text-slate-500">{post.excerpt}</p>}
        {yieldText && (
          <p className="mt-3 inline-flex rounded-full bg-brand-50 px-3 py-1 text-sm font-semibold text-brand-800">
            {yieldText}
          </p>
        )}
        {cover && (
          <div className="mt-6 overflow-hidden rounded-2xl bg-slate-100">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={cover} alt={post.title_vi} className="max-h-[420px] w-full object-cover" />
          </div>
        )}
        {ingredients.length > 0 && (
          <section className="mt-6">
            <h2 className="text-lg font-bold">Nguyên liệu và khối lượng</h2>
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              {ingredients.map((item, idx) => (
                <IngredientCard key={`${item.food_slug || "ing"}-${idx}`} item={item} />
              ))}
            </div>
          </section>
        )}
        <div
          className="mt-6 rounded-2xl bg-white p-6 shadow-soft text-[15px]"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content_md) }}
        />
      </article>
    </div>
  );
}
