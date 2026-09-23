import PlanAiBuilder from "@/components/PlanAiBuilder";
import { BRAND_NAME } from "@/lib/brand";
import { redirect } from "next/navigation";

export const metadata = { title: `Bắt đầu với ${BRAND_NAME}` };

export default async function PlanTaptotPage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string; paid?: string; orderId?: string }>;
}) {
  const params = await searchParams;
  const code = (params.code || "").trim();
  if (code && !params.paid && !params.orderId) {
    redirect(`/batdau/${encodeURIComponent(code)}`);
  }
  return <PlanAiBuilder />;
}
