import PlanAiBuilder from "@/components/PlanAiBuilder";
import { BRAND_NAME } from "@/lib/brand";

export const metadata = { title: `Bắt đầu với ${BRAND_NAME}` };

type PageProps = { params: Promise<{ ma: string }> };

export default async function BatdauCodePage({ params }: PageProps) {
  const { ma } = await params;
  let decoded = ma;
  try {
    decoded = decodeURIComponent(ma);
  } catch {
    decoded = ma;
  }
  return <PlanAiBuilder initialGiftCode={decoded} codeFromPath />;
}
