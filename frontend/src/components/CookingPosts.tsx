"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { mediaUrl } from "@/lib/labels";
import type { CookingPost } from "@/lib/types";

export default function CookingPosts({ basePath = "/cach-nau" }: { basePath?: string }) {
  const [items, setItems] = useState<CookingPost[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    cookingPostsApi
      .listPublic(1, 50)
      .then((d) => setItems(d.items || []))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <section>
      <div className="mb-6">
        <h1 className="text-2xl font-extrabold tracking-tight">Cách nấu món ăn ngon</h1>
        <p className="mt-1 text-sm text-slate-500">
          Công thức và mẹo nấu từ kho thực phẩm TAPTOT — dễ làm tại nhà.
        </p>
      </div>

      {error && <div className="py-12 text-center text-rose-500">Lỗi tải dữ liệu: {error}</div>}

      {loading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-56 animate-pulse rounded-2xl bg-white shadow-soft" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="py-16 text-center text-slate-400">
          <p className="font-medium">Chưa có bài viết. Quay lại sau nhé.</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((p) => {
            const cover = mediaUrl(p.cover_image_url);
            return (
              <Link
                key={p.id}
                href={`${basePath}/${p.slug}`}
                className="group flex flex-col overflow-hidden rounded-2xl bg-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
              >
                <div className="h-40 bg-gradient-to-br from-accent-100 to-accent-200">
                  {cover ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={cover} alt={p.title_vi} className="h-full w-full object-cover" />
                  ) : (
                    <div className="grid h-full place-items-center text-4xl">🍳</div>
                  )}
                </div>
                <div className="flex flex-1 flex-col p-5">
                  <h2 className="font-bold leading-snug group-hover:text-brand-700">{p.title_vi}</h2>
                  {p.excerpt && (
                    <p className="mt-2 line-clamp-2 flex-1 text-sm text-slate-500">{p.excerpt}</p>
                  )}
                  <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold text-brand-600">
                    Đọc bài
                    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                      <path d="M5 12h14M13 6l6 6-6 6" />
                    </svg>
                  </span>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </section>
  );
}
