import { Suspense } from "react";
import { redirect } from "next/navigation";
import GiftCodeLanding from "@/components/GiftCodeLanding";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Mã trên tem${BRAND_TITLE_SUFFIX}`,
  description: "Nhập hoặc quét mã trên tem sản phẩm để tạo lịch tập TAPTOT.",
};

async function GiftRedirect({
  searchParams,
}: {
  searchParams: Promise<{ code?: string }>;
}) {
  const params = await searchParams;
  const code = (params.code || "").trim();
  if (code) {
    redirect(`/batdau/${encodeURIComponent(code)}`);
  }
  return <GiftCodeLanding />;
}

export default function GiftCodePage({
  searchParams,
}: {
  searchParams: Promise<{ code?: string }>;
}) {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Đang tải…</p>}>
      <GiftRedirect searchParams={searchParams} />
    </Suspense>
  );
}
