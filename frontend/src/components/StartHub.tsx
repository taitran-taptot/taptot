import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";

const PATHS = [
  {
    id: "coach",
    title: "Tập với HLV chuyên nghiệp",
    desc: "Muốn có người kèm riêng, chỉnh form và theo sát tiến độ? Kết nối huấn luyện viên collab với TAPTOT.",
    cta: "Gặp HLV",
    href: "/lien-he",
    tone: "light" as const,
  },
  {
    id: "challenge",
    title: "Thử thách bản thân với TAPTOT",
    desc: "Không ai mãi yếu kém, không ai mãi xấu. Chỉ có người không chịu thay đổi.",
    cta: "Bắt đầu",
    href: "/tao-lich-tap/taptot",
    tone: "orange" as const,
  },
  {
    id: "diy",
    title: "Tự tạo lịch tập",
    desc: "Bạn tự chọn mục tiêu, bài tập và nhịp tập — kiểm soát hoàn toàn lịch của mình.",
    cta: "Tự tạo lịch",
    href: "/tao-lich-tap/tu-tao",
    tone: "green" as const,
  },
];

export default function StartHub() {
  return (
    <div className="space-y-10 pb-4">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 shadow-soft ring-1 ring-brand-100/60 sm:px-10 sm:py-12">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Bắt đầu</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Chọn cách hợp bạn
        </h1>
        <p className="mt-3 max-w-xl text-base leading-relaxed text-slate-600 sm:text-lg">
          Có người kèm, thử thách 100 ngày với {BRAND_NAME}, hoặc tự xếp lịch — không bắt phải một kiểu.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-3">
        {PATHS.map((p) => (
          <section
            key={p.id}
            className={`relative flex flex-col overflow-hidden rounded-3xl p-6 shadow-soft sm:p-7 ${
              p.tone === "orange"
                ? "bg-gradient-to-br from-orange-50 via-amber-50 to-orange-100 ring-1 ring-orange-200"
                : p.tone === "green"
                  ? "bg-gradient-to-br from-brand-50 to-emerald-50 ring-1 ring-brand-100"
                  : "bg-white ring-1 ring-slate-100"
            }`}
          >
            {p.tone === "orange" && (
              <div className="pointer-events-none absolute inset-x-0 top-0 h-1 bg-orange-400" />
            )}
            <h2
              className="text-xl font-extrabold tracking-tight text-slate-900"
            >
              {p.title}
            </h2>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-slate-600">{p.desc}</p>
            <Link
              href={p.href}
              className={`mt-6 inline-flex w-fit items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold shadow-soft transition ${
                p.tone === "orange"
                  ? "bg-orange-500 text-white hover:bg-orange-600"
                  : "bg-brand-500 text-white hover:bg-brand-600"
              }`}
            >
              {p.cta}
              <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </Link>
          </section>
        ))}
      </div>
    </div>
  );
}
