import TermsDocument from "@/components/TermsDocument";
import Footer from "@/components/Footer";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { TERMS_TITLE } from "@/lib/terms";

export const metadata = {
  title: `${TERMS_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Điều khoản sử dụng và miễn trừ trách nhiệm y tế của TAPTOT — lịch tập và thực đơn chỉ mang tính tham khảo, không thay thế lời khuyên y khoa.",
};

export default function DieuKhoanPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Pháp lý</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Điều khoản sử dụng
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Và miễn trừ trách nhiệm y tế. Đọc trước khi nhận lịch hoặc thanh toán.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <TermsDocument heading={false} />
      </div>
      <Footer />
    </div>
  );
}
