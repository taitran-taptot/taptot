"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { mediaUrl } from "@/lib/labels";
import { renderMarkdown } from "@/lib/markdown";
import type { CookingPost } from "@/lib/types";

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
    return <div className="h-64 animate-pulse rounded-2xl bg-white shadow-soft" />;
  }
  if (error || !post) {
    return (
      <div className="py-16 text-center">
        <p className="text-rose-500">{error || "Không tìm thấy bài viết"}</p>
        <Link href={listHref} className="mt-4 inline-block text-sm font-semibold text-brand-600">
          ← Tất cả bài nấu ăn
        </Link>
      </div>
    );
  }

  const cover = mediaUrl(post.cover_image_url);

  return (
    <article className="mx-auto max-w-3xl">
      <Link href={listHref} className="text-sm font-semibold text-brand-600 hover:text-brand-700">
        ← Cách nấu món ăn ngon
      </Link>
      <h1 className="mt-4 text-3xl font-extrabold tracking-tight">{post.title_vi}</h1>
      {post.excerpt && <p className="mt-2 text-slate-500">{post.excerpt}</p>}
      {cover && (
        <div className="mt-6 overflow-hidden rounded-2xl bg-slate-100">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={cover} alt="" className="max-h-[420px] w-full object-cover" />
        </div>
      )}
      <div
        className="mt-6 rounded-2xl bg-white p-6 shadow-soft text-[15px]"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(post.content_md) }}
      />
    </article>
  );
}
