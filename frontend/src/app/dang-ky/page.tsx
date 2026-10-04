import Link from "next/link";

export const metadata = { title: "Đăng ký — TAPTOT" };

export default function RegisterPage() {
  return (
    <section className="py-6">
      <div className="mx-auto max-w-md space-y-4 rounded-2xl bg-white p-6 shadow-soft">
        <h1 className="type-display">Đăng ký đã đóng</h1>
        <p className="text-sm text-slate-600">
          Tài khoản khách không còn được tạo công khai. HLV được Admin thêm trong phần quản trị.
        </p>
        <Link
          href="/dang-nhap"
          className="inline-flex rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
        >
          Đăng nhập HLV / Admin
        </Link>
      </div>
    </section>
  );
}
