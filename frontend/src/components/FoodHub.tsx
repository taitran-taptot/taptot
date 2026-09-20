"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { cookingPostsApi } from "@/lib/cookingPostsApi";
import { foodDisplayName, foodKcalLine } from "@/lib/foodDisplay";
import { mediaUrl } from "@/lib/labels";
import type { CookingPost, Food } from "@/lib/types";

const SECTIONS = [
  {
    id: "foods",
    title: "Thực phẩm",
    desc: "Chọn nguyên liệu, xem calo theo chén / quả — như đi chợ.",
    cta: "Vào quầy thực phẩm",
    href: "/thuc-an",
    tone: "light" as const,
  },
  {
    id: "dishes",
    title: "Món truyền thống",
    desc: "Phở, bún, cơm tấm và món Việt quen thuộc.",
    cta: "Xem món truyền thống",
    href: "/thuc-an?tab=dishes",
    tone: "warm" as const,
  },
  {
    id: "cook",
    title: "Cách nấu món ngon",
    desc: "Công thức quen thuộc, dễ làm tại nhà.",
    cta: "Xem cách nấu",
    href: "/cach-nau",
    tone: "green" as const,
  },
];

function pickPreviewFoods(items: Food[], limit: number): Food[] {
  const withPhoto = items.filter((f) => Boolean(f.image_url));
  const withoutPhoto = items.filter((f) => !f.image_url);
  return [...withPhoto, ...withoutPhoto].slice(0, limit);
}

export default function FoodHub() {
  const [ingredients, setIngredients] = useState<Food[]>([]);
  const [dishes, setDishes] = useState<Food[]>([]);
  const [posts, setPosts] = useState<CookingPost[]>([]);

  useEffect(() => {
    api
      .searchFoods({ page: 1, page_size: 40, is_common: true })
      .then((res) => {
        const items = res.items || [];
        const ingredients = items.filter((f) => (f.food_kind || "ingredient") !== "dish");
        const dishes = items.filter((f) => f.food_kind === "dish");
        setIngredients(pickPreviewFoods(ingredients, 4));
        setDishes(pickPreviewFoods(dishes, 4));
      })
      .catch(() => {});

    cookingPostsApi
      .listPublic(1, 3)
      .then((d) => setPosts((d.items || []).slice(0, 3)))
      .catch(() => {});
  }, []);

  return (
    <div className="space-y-12 pb-4">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Ăn uống</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Kho thực phẩm
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Thịt, rau, cơm — món Việt quen và cách nấu tại nhà. Chọn một quầy bên dưới để bắt đầu.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-3">
        {SECTIONS.map((s) => (
          <section
            key={s.id}
            className={`flex flex-col rounded-3xl p-6 shadow-soft sm:p-7 ${
              s.tone === "light"
                ? "bg-white ring-1 ring-slate-100"
                : s.tone === "warm"
                  ? "bg-gradient-to-br from-orange-50 to-amber-50 ring-1 ring-orange-100"
                  : "bg-gradient-to-br from-brand-50 to-emerald-50 ring-1 ring-brand-100"
            }`}
          >
            <h2 className="text-xl font-extrabold tracking-tight text-slate-900">{s.title}</h2>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{s.desc}</p>
            <Link
              href={s.href}
              className="mt-5 inline-flex w-fit items-center gap-2 rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
            >
              {s.cta}
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
          </section>
        ))}
      </div>

      {(ingredients.length > 0 || dishes.length > 0 || posts.length > 0) && (
        <section className="space-y-8">
          <div>
            <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Mới trong kho</h2>
            <p className="mt-1 text-sm text-slate-500">Vài gợi ý quen thuộc — bấm để xem thêm trong từng quầy.</p>
          </div>

          {ingredients.length > 0 && (
            <PreviewBlock
              title="Thực phẩm gợi ý"
              href="/thuc-an"
              items={ingredients.map((f) => ({
                key: String(f.id),
                href: "/thuc-an",
                title: foodDisplayName(f.name_vi),
                meta: foodKcalLine(f),
                image: mediaUrl(f.image_url),
              }))}
            />
          )}

          {dishes.length > 0 && (
            <PreviewBlock
              title="Món truyền thống"
              href="/thuc-an?tab=dishes"
              items={dishes.map((f) => ({
                key: String(f.id),
                href: "/thuc-an?tab=dishes",
                title: foodDisplayName(f.name_vi),
                meta: foodKcalLine(f),
                image: mediaUrl(f.image_url),
              }))}
            />
          )}

          {posts.length > 0 && (
            <PreviewBlock
              title="Cách nấu gần đây"
              href="/cach-nau"
              items={posts.map((p) => ({
                key: p.slug,
                href: `/cach-nau/${p.slug}`,
                title: p.title_vi,
                meta: p.excerpt || "Công thức dễ làm",
                image: mediaUrl(p.cover_image_url),
              }))}
            />
          )}
        </section>
      )}
    </div>
  );
}

function PreviewBlock({
  title,
  href,
  items,
}: {
  title: string;
  href: string;
  items: { key: string; href: string; title: string; meta: string; image?: string | null }[];
}) {
  return (
    <div>
      <div className="mb-3 flex items-end justify-between gap-3">
        <h3 className="font-bold text-slate-800">{title}</h3>
        <Link href={href} className="text-sm font-semibold text-brand-600 hover:text-brand-700">
          Xem tất cả
        </Link>
      </div>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {items.map((item) => (
          <li key={item.key}>
            <Link
              href={item.href}
              className="flex h-full flex-col overflow-hidden rounded-2xl bg-white shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-1 hover:ring-brand-100"
            >
              {item.image ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={item.image} alt={item.title} className="h-28 w-full object-cover" />
              ) : (
                <div className="grid h-28 place-items-center bg-gradient-to-br from-brand-50 to-emerald-50 text-xs font-semibold text-brand-700">
                  TAPTOT
                </div>
              )}
              <div className="flex flex-1 flex-col p-3.5">
                <p className="font-semibold text-slate-900">{item.title}</p>
                <p className="mt-1 line-clamp-2 text-xs text-slate-500">{item.meta}</p>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
