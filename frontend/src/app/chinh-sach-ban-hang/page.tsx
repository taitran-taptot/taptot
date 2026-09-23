import SalesPolicyDocument from "@/components/SalesPolicyDocument";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { SALES_POLICY_TITLE } from "@/lib/salesPolicy";

export const metadata = {
  title: `${SALES_POLICY_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Chính sách bán hàng TAPTOT — đặt phụ kiện, giao nhận, đổi trả, mã ưu đãi và thanh toán gói.",
};

export default function ChinhSachBanHangPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="type-kicker text-brand-600">Pháp lý</p>
        <h1 className="mt-2 type-display">Chính sách bán hàng</h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Đặt hàng phụ kiện, giao nhận, đổi trả, mã ưu đãi và thanh toán gói khi được bật.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <SalesPolicyDocument heading={false} />
      </div>
    </div>
  );
}
