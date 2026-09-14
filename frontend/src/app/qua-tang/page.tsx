import { Suspense } from "react";
import GiftCodeLanding from "@/components/GiftCodeLanding";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";

export const metadata = {
  title: `Mã trên tem${BRAND_TITLE_SUFFIX}`,
  description: "Nhập hoặc quét mã trên tem sản phẩm để tạo lịch tập TAPTOT.",
};

export default function GiftCodePage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Đang tải…</p>}>
      <GiftCodeLanding />
    </Suspense>
  );
}
