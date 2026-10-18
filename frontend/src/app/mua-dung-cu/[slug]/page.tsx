import type { Metadata } from "next";
import ShopProductDetail from "@/components/ShopProductDetail";
import { API_BASE } from "@/lib/config";

type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  try {
    const res = await fetch(`${API_BASE.replace(/\/$/, "")}/shop/products/slug/${encodeURIComponent(slug)}`, {
      next: { revalidate: 60 },
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return { title: "Dụng cụ — TAPTOT" };
    const product = (await res.json()) as { name_vi?: string };
    return {
      title: `${product.name_vi || "Dụng cụ"} — TAPTOT`,
      description: "Thông tin, cách dùng và mua dụng cụ TAPTOT.",
    };
  } catch {
    return { title: "Dụng cụ — TAPTOT" };
  }
}

export default async function ShopProductPage({ params }: PageProps) {
  const { slug } = await params;
  return <ShopProductDetail slug={slug} />;
}
