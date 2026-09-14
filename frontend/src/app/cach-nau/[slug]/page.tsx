import CookingPostDetail from "@/components/CookingPostDetail";

type PageProps = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: PageProps) {
  const { slug } = await params;
  return { title: `${slug} — Cách nấu món ăn ngon — TAPTOT` };
}

export default async function CookingDetailPage({ params }: PageProps) {
  const { slug } = await params;
  return <CookingPostDetail slug={slug} />;
}
