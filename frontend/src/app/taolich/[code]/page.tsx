import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import TaolichEntry from "@/components/fitness-test/TaolichEntry";

export const metadata = {
  title: `Tạo lịch${BRAND_TITLE_SUFFIX}`,
};

type PageProps = { params: Promise<{ code: string }> };

export default async function TaolichPage({ params }: PageProps) {
  const { code } = await params;
  return <TaolichEntry code={code} />;
}
