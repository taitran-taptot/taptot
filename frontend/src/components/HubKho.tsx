import Link from "next/link";

const ITEMS = [
  {
    href: "/kho-bai-tap",
    title: "Kho bài tập",
    desc: "Bài tập và dụng cụ — mở khi bạn cần.",
  },
  {
    href: "/tai-khoan/thuc-an",
    title: "Thức ăn",
    desc: "Calo theo khẩu phần Việt — 1 chén, 1 quả.",
  },
  {
    href: "/tai-khoan/cach-nau",
    title: "Cách nấu",
    desc: "Công thức món quen, nấu tại nhà.",
  },
  {
    href: "/tai-khoan/kien-thuc",
    title: "Kiến thức",
    desc: "Bài ngắn cho người mới, tiếng Việt.",
  },
  {
    href: "/tai-khoan/dung-cu",
    title: "Dụng cụ",
    desc: "Xem dụng cụ và bài tập đi kèm.",
  },
  {
    href: "/tai-khoan/mua-dung-cu",
    title: "Mua dụng cụ",
    desc: "Đặt hàng trên TAPTOT — chưa thanh toán online.",
  },
  {
    href: "/tai-khoan/may-tinh-calo",
    title: "Máy tính calo",
    desc: "Ước lượng calo mỗi ngày cho mục tiêu của bạn.",
  },
  {
    href: "/bat-dau",
    title: "Bắt đầu",
    desc: "HLV, thử thách 100 ngày, hoặc tự tạo lịch.",
  },
];

export default function HubKho() {
  return (
    <section className="space-y-5">
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Kho</h1>
        <p className="mt-1 text-sm text-slate-500">Bài tập, ăn uống, kiến thức — mở khi bạn cần.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {ITEMS.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="rounded-2xl bg-white p-5 shadow-soft transition hover:ring-2 hover:ring-brand-200"
          >
            <h2 className="font-bold text-slate-800">{item.title}</h2>
            <p className="mt-1 text-sm text-slate-500">{item.desc}</p>
          </Link>
        ))}
      </div>
    </section>
  );
}
