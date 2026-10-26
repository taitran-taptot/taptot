import PaymentPolicyDocument from "@/components/PaymentPolicyDocument";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { PAYMENT_POLICY_TITLE } from "@/lib/paymentPolicy";

export const metadata = {
  title: `${PAYMENT_POLICY_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Chính sách thanh toán TAPTOT — chuyển khoản ngân hàng, COD, hoàn tiền khi hủy đơn và thời hạn xem lịch tập.",
};

export default function ChinhSachThanhToanPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="type-kicker text-brand-600">Pháp lý</p>
        <h1 className="mt-2 type-display">Thanh toán và hoàn tiền</h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Chuyển khoản ngân hàng hoặc COD. Hoàn tiền chuyển khoản khi đơn bị hủy.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <PaymentPolicyDocument heading={false} />
      </div>
    </div>
  );
}
