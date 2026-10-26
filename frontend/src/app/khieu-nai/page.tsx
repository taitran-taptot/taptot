import ComplaintDocument from "@/components/ComplaintDocument";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { COMPLAINT_TITLE } from "@/lib/complaintPolicy";

export const metadata = {
  title: `${COMPLAINT_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Cách gửi khiếu nại TAPTOT về đơn hàng, lịch tập và dữ liệu cá nhân, cùng thời hạn phản hồi cam kết.",
};

export default function KhieuNaiPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="type-kicker text-brand-600">Pháp lý</p>
        <h1 className="mt-2 type-display">Khiếu nại</h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Gửi qua email, Zalo hoặc form góp ý. Chúng tôi xác nhận và trả lời theo các bước trên trang.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <ComplaintDocument heading={false} />
      </div>
    </div>
  );
}
