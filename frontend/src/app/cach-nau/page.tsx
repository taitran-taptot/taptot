import CookingPostDetail from "@/components/CookingPostDetail";
import CookingPosts from "@/components/CookingPosts";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

type PageProps = {
  searchParams: Promise<{ mon?: string; slug?: string }>;
};

export async function generateMetadata({ searchParams }: PageProps) {
  const sp = await searchParams;
  const mon = (sp.mon || sp.slug || "").trim();
  if (mon) {
    return {
      title: `${mon} — Cách nấu món ăn ngon${BRAND_TITLE_SUFFIX}`,
    };
  }
  return {
    title: `Cách nấu món ăn ngon${BRAND_TITLE_SUFFIX}`,
    description:
      "Ảnh, công thức và mẹo nấu từ kho thực phẩm TAPTOT do AI tạo/tổng hợp, chỉ mang tính tham khảo — không thay tư vấn dinh dưỡng hay y tế.",
  };
}

export default async function CookingPage({ searchParams }: PageProps) {
  const sp = await searchParams;
  const mon = (sp.mon || sp.slug || "").trim();
  if (mon) {
    return <CookingPostDetail slug={mon} />;
  }
  return <CookingPosts />;
}
