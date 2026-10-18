import PlanAiBuilder from "@/components/PlanAiBuilder";
import { BRAND_NAME } from "@/lib/brand";

export const metadata = { title: `Bắt đầu với ${BRAND_NAME}` };

export default async function PlanTaptotPage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string; paid?: string }>;
}) {
  const params = await searchParams;
  const code = (params.code || "").trim();
  if (code && !params.paid) {
    return <PlanAiBuilder initialGiftCode={code} codeFromPath />;
  }
  return <PlanAiBuilder />;
}
