import type { Metadata } from "next";
import { Suspense } from "react";
import PlanShareView from "@/components/PlanShareView";
import { API_BASE } from "@/lib/config";
import { BRAND_NAME, BRAND_TITLE_SUFFIX } from "@/lib/brand";

type PageProps = { searchParams: Promise<{ token?: string }> };

async function fetchShareMeta(token: string): Promise<{
  title_vi?: string;
  description_vi?: string | null;
  target_calories?: number | null;
  day_count?: number;
} | null> {
  try {
    const res = await fetch(`${API_BASE}/plans/share/${encodeURIComponent(token)}`, {
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    const data = await res.json();
    return {
      title_vi: data.title_vi,
      description_vi: data.description_vi,
      target_calories: data.target_calories,
      day_count: Array.isArray(data.days) ? data.days.length : data.day_count,
    };
  } catch {
    return null;
  }
}

export async function generateMetadata({ searchParams }: PageProps): Promise<Metadata> {
  const { token: raw } = await searchParams;
  const token = (raw || "").trim();
  const plan = token ? await fetchShareMeta(token) : null;
  const title = plan?.title_vi
    ? `${plan.title_vi}${BRAND_TITLE_SUFFIX}`
    : `Lịch tập ${BRAND_NAME}`;
  const bits: string[] = [];
  if (plan?.day_count) bits.push(`${plan.day_count} buổi`);
  if (plan?.target_calories != null) bits.push(`~${plan.target_calories} calo/ngày`);
  const description =
    (plan?.description_vi && String(plan.description_vi).slice(0, 160)) ||
    (bits.length
      ? `Lịch tập ${BRAND_NAME}: ${bits.join(" · ")}. Mở link để xem bài tập và thực đơn.`
      : `Xem lịch tập và thực đơn trên ${BRAND_NAME}.`);

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      type: "website",
      images: [{ url: "/og-plan.svg", width: 1200, height: 630, alt: BRAND_NAME }],
    },
    twitter: {
      card: "summary_large_image",
      title,
      description,
      images: ["/og-plan.svg"],
    },
  };
}

export default async function Page({ searchParams }: PageProps) {
  const { token: raw } = await searchParams;
  return (
    <Suspense fallback={<p className="py-10 text-center text-sm text-slate-400">Đang mở lịch…</p>}>
      <PlanShareView token={(raw || "").trim()} />
    </Suspense>
  );
}
