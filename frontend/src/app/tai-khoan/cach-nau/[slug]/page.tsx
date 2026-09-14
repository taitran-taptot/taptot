import CookingPostDetail from "@/components/CookingPostDetail";

type PageProps = { params: Promise<{ slug: string }> };

export default async function AccountCookingDetailPage({ params }: PageProps) {
  const { slug } = await params;
  return <CookingPostDetail slug={slug} listHref="/tai-khoan/cach-nau" />;
}
