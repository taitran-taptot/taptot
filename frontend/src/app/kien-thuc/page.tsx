import { Suspense } from "react";
import type { Metadata } from "next";
import KnowledgeBase from "@/components/KnowledgeBase";
import { api } from "@/lib/api";
import { canonicalizeKnowledgeSlug } from "@/lib/knowledgeSlugAliases";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

type PageProps = { searchParams: Promise<{ bai?: string; slug?: string }> };

const INDEX_META: Metadata = {
  title: `Kho kiến thức${BRAND_TITLE_SUFFIX}`,
  description: "Kho kiến thức TAPTOT.",
};

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  const sp = await searchParams;
  const slug = canonicalizeKnowledgeSlug((sp.bai || sp.slug || "").trim());
  if (!slug) return INDEX_META;
  try {
    const data = await api.knowledgeArticles();
    const article = (data.items || []).find((row) => row.slug === slug && row.is_published !== false);
    if (!article) return INDEX_META;
    return {
      title: `${article.seo_title || article.title_vi}${BRAND_TITLE_SUFFIX}`,
      description: article.seo_description || INDEX_META.description,
    };
  } catch {
    return INDEX_META;
  }
}

export default async function KnowledgePage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const initialSlug = canonicalizeKnowledgeSlug((sp.bai || sp.slug || "").trim());
  return (
    <Suspense
      fallback={
        <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[18rem_1fr]">
          <div className="h-80 animate-pulse rounded-3xl bg-white shadow-soft" />
          <div className="min-h-80 animate-pulse rounded-3xl bg-white shadow-soft" />
        </div>
      }
    >
      <KnowledgeBase initialSlug={initialSlug} />
    </Suspense>
  );
}
