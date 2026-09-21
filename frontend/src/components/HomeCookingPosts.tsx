"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { mediaUrl } from "@/lib/labels";
import type { CookingPost } from "@/lib/types";

export default function HomeCookingPosts({
  basePath = "/cach-nau",
  compact = false,
  title = "Cách nấu món ăn ngon",
  cta = "Xem tất cả",
}: {
  basePath?: string;
  compact?: boolean;
  title?: string;
  cta?: string;
}) {
  const [items, setItems] = useState<CookingPost[]>([]);

  useEffect(() => {
    cookingPostsApi
      .listPublic(1, 3)
      .then((d) => setItems((d.items || []).slice(0, 3)))
      .catch(() => {});
  }, []);

  if (items.length === 0) return null;

  return (
    <section>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2
            className={
              compact
                ? "type-title"
                : "type-display"
            }
          >
            {title}
          </h2>
          <p className={`max-w-xl text-slate-500 ${compact ? "mt-1 text-sm" : "mt-2"}`}>
            {compact
              ? "Công thức quen thuộc, dễ làm tại nhà."
              : "Bài mới từ kho thực phẩm — công thức dễ làm tại nhà."}
          </p>
        </div>
        <Link href={basePath} className="text-sm font-semibold text-brand-600 hover:text-brand-700">
          {cta} →
        </Link>
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {items.map((p) => {
          const cover = mediaUrl(p.cover_image_url);
          return (
            <Link
              key={p.id}
                href={`${basePath}/${p.slug}`}
              className="group overflow-hidden rounded-2xl bg-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
            >
              <div className="h-36 bg-gradient-to-br from-accent-100 to-accent-200">
                {cover ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={cover} alt={p.title_vi} className="h-full w-full object-cover" />
                ) : (
                  <div className="grid h-full place-items-center text-3xl">🍳</div>
                )}
              </div>
              <div className="p-4">
                <h3 className="font-bold group-hover:text-brand-700">{p.title_vi}</h3>
                {p.excerpt && <p className="mt-1 line-clamp-2 text-sm text-slate-500">{p.excerpt}</p>}
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
