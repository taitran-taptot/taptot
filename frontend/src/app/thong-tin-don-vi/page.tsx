import OperatorDocument from "@/components/OperatorDocument";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { OPERATOR_TITLE } from "@/lib/operatorInfo";

export const metadata = {
  title: `${OPERATOR_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Thông tin đơn vị vận hành TAPTOT — thương hiệu, email, điện thoại và các mục tên pháp nhân, mã số thuế đang cập nhật.",
};

export default function ThongTinDonViPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="type-kicker text-brand-600">Pháp lý</p>
        <h1 className="mt-2 type-display">Thông tin đơn vị</h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Thương hiệu, kênh liên hệ và phần đăng ký sẽ được điền khi có giấy tờ.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <OperatorDocument heading={false} />
      </div>
    </div>
  );
}
