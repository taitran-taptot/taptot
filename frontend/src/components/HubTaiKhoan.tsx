"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { getStoredUser, clearAuth } from "@/lib/auth";
import { LOGOUT_EVENT } from "@/lib/http";

const LINKS = [
  { href: "/tai-khoan/ke-hoach", title: "Lịch của tôi", desc: "Xem lịch đã lưu và đổi bài thay thế." },
  { href: "/tai-khoan/don-hang", title: "Đơn hàng", desc: "Dụng cụ đã đặt." },
  { href: "/tai-khoan/doi-mat-khau", title: "Đổi mật khẩu", desc: "Bảo vệ tài khoản của bạn." },
];

const ADMIN_LINKS = [
  { href: "/tai-khoan/quan-tri/bai-tap", title: "Quản trị bài tập", desc: "Thêm, sửa bài tập." },
  { href: "/tai-khoan/quan-tri/dung-cu", title: "Quản trị dụng cụ", desc: "Thông số sản phẩm cho AI." },
  { href: "/tai-khoan/quan-tri/thuc-an", title: "Quản trị thức ăn", desc: "Thêm, sửa thức ăn." },
  { href: "/tai-khoan/quan-tri/san-pham", title: "Quản trị sản phẩm", desc: "Sản phẩm shop và mã." },
  { href: "/tai-khoan/quan-tri/ma-qua-tang", title: "Mã trên tem", desc: "QR / mã quà tặng trên sản phẩm." },
];

export default function HubTaiKhoan() {
  const router = useRouter();
  const user = getStoredUser();
  const links = user?.role === "admin" ? [...LINKS, ...ADMIN_LINKS] : LINKS;

  async function logout() {
    const { authApi } = await import("@/lib/authApi");
    await authApi.logout();
    clearAuth();
    window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    router.push("/");
  }

  return (
    <section className="space-y-5">
      <div>
        <h1 className="type-display">Tài khoản</h1>
        <p className="mt-1 text-sm text-slate-500">
          {user?.display_name || user?.email || "Người tập TAPTOT"}
        </p>
      </div>
      <div className="space-y-3">
        {links.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="block rounded-2xl bg-white p-5 shadow-soft transition hover:ring-2 hover:ring-brand-200"
          >
            <h2 className="font-bold text-slate-800">{item.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{item.desc}</p>
          </Link>
        ))}
      </div>
      <button
        type="button"
        onClick={() => void logout()}
        className="w-full rounded-xl border border-rose-200 bg-white px-4 py-3 text-sm font-bold text-rose-600 hover:bg-rose-50"
      >
        Đăng xuất
      </button>
    </section>
  );
}
