import PrivacyDocument from "@/components/PrivacyDocument";
import { BRAND_TITLE_SUFFIX } from "@/lib/brand";
import { PRIVACY_TITLE } from "@/lib/privacy";

export const metadata = {
  title: `${PRIVACY_TITLE}${BRAND_TITLE_SUFFIX}`,
  description:
    "Chính sách bảo mật TAPTOT — cách chúng tôi thu thập và bảo vệ dữ liệu tài khoản, thể trạng, lịch tập, đơn hàng và camera thử thách.",
};

export default function ChinhSachBaoMatPage() {
  return (
    <div className="space-y-8 pb-8">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-amber-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="type-kicker text-brand-600">Pháp lý</p>
        <h1 className="mt-2 type-display">Chính sách bảo mật</h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Dữ liệu cá nhân, cookie phiên, camera trên thiết bị và bên thứ ba xử lý hộ.
        </p>
      </header>
      <div className="rounded-3xl bg-white px-6 py-8 shadow-soft ring-1 ring-slate-100 sm:px-10 sm:py-10">
        <PrivacyDocument heading={false} />
      </div>
    </div>
  );
}
