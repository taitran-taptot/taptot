import Link from "next/link";
import { BRAND_NAME } from "@/lib/brand";

const SHOP_HREF = "/mua-dung-cu?from=challenge";
const GIFT_HREF = "/qua-tang";

const PHASES = [
  {
    n: "1",
    weeks: "Tuần 1–4",
    title: "Làm quen & dựng nền",
    desc: "Tập vừa sức, quen nhịp sống mới.",
  },
  {
    n: "2",
    weeks: "Tuần 5–8",
    title: "Tăng dần độ khó",
    desc: "Tăng dần cường độ, bước vào giai đoạn thay đổi rõ rệt.",
  },
  {
    n: "3",
    weeks: "Tuần 9–14",
    title: "Củng cố thói quen",
    desc: "Giữ nhịp dài hạn, kết thúc thử thách vững vàng.",
  },
];

const BENEFITS = [
  {
    title: "Lịch tập cá nhân",
    desc: "Lịch tập cá nhân hóa với thời gian biểu của bạn, có video hướng dẫn tập và đi kèm giải thích dễ hiểu giúp bạn nhanh chóng làm quen.",
  },
  {
    title: "Thực đơn cá nhân hóa",
    desc: "Ăn chế độ nhưng không hề gò bó, bạn có thể chọn món ăn mình muốn ăn nhưng vẫn đạt được mục tiêu thay đổi vóc dáng.",
  },
];

const WHO = [
  "Muốn thay đổi vóc dáng bản thân nhưng chưa biết bắt đầu từ đâu.",
  "Muốn dáng đẹp nhưng vẫn muốn ăn linh hoạt, chế độ ăn không quá khắt khe.",
  "Muốn có một lịch trình rõ ràng phù hợp với mục tiêu.",
];

export default function Challenge100Landing() {
  return (
    <div className="mx-auto max-w-3xl space-y-10 pb-4">
      <section className="rounded-3xl bg-gradient-to-br from-brand-600 to-brand-800 px-6 py-12 text-center text-white shadow-soft sm:px-10 sm:py-16">
        <p className="text-sm font-semibold tracking-wide text-white/80">{BRAND_NAME}</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight sm:text-4xl">Thử thách 100 ngày</h1>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href={SHOP_HREF}
            className="w-full rounded-xl bg-white px-7 py-3.5 text-base font-bold text-brand-700 shadow-soft transition hover:bg-brand-50 sm:w-auto"
          >
            Chọn dụng cụ · Nhận lộ trình 100 ngày
          </Link>
          <Link
            href={GIFT_HREF}
            className="w-full rounded-xl border border-white/30 bg-white/10 px-7 py-3.5 text-base font-bold text-white transition hover:bg-white/15 sm:w-auto"
          >
            Tôi đã có mã
          </Link>
        </div>
      </section>

      <section>
        <h2 className="text-center text-xl font-extrabold tracking-tight sm:text-2xl">Vì sao 100 ngày?</h2>
        <p className="mx-auto mt-2 max-w-xl text-center text-sm leading-relaxed text-slate-500 sm:text-base">
          Vì 100 ngày là thời gian đủ dài để bạn tạo dựng thói quen lành mạnh và cũng là khoảng thời gian đủ để bạn
          thấy cơ thể thay đổi thành một phiên bản tốt hơn.
        </p>
      </section>

      <section>
        <h2 className="text-center text-xl font-extrabold tracking-tight sm:text-2xl">Thử thách gồm những gì</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {PHASES.map((p) => (
            <div key={p.n} className="rounded-2xl bg-white p-5 shadow-soft">
              <p className="grid h-9 w-9 place-items-center rounded-full bg-brand-100 text-sm font-extrabold text-brand-700">
                {p.n}
              </p>
              <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-brand-600">{p.weeks}</p>
              <h3 className="mt-1 font-bold text-slate-900">{p.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-center text-xl font-extrabold tracking-tight sm:text-2xl">Bạn nhận được gì</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {BENEFITS.map((b) => (
            <div key={b.title} className="rounded-2xl border border-slate-100 bg-white px-5 py-4">
              <h3 className="font-bold text-slate-900">{b.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-500">{b.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl bg-white p-6 shadow-soft sm:p-8">
        <h2 className="text-xl font-extrabold tracking-tight sm:text-2xl">Ai hợp với thử thách này?</h2>
        <ul className="mt-4 space-y-2.5">
          {WHO.map((line) => (
            <li key={line} className="flex gap-2.5 text-sm leading-relaxed text-slate-600">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" aria-hidden />
              {line}
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-3xl bg-slate-900 px-6 py-10 text-center text-white sm:px-10 sm:py-12">
        <h2 className="text-2xl font-extrabold tracking-tight">Lộ trình được tặng cùng dụng cụ TAPTOT</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-slate-300">
          Chọn dụng cụ phù hợp, nhận mã trên tem rồi tạo lịch tập và lịch ăn của riêng bạn.
        </p>
        <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href={SHOP_HREF}
            className="inline-flex w-full items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white transition hover:bg-brand-600 sm:w-auto"
          >
            Chọn dụng cụ
          </Link>
          <Link
            href={GIFT_HREF}
            className="inline-flex w-full items-center justify-center rounded-xl border border-white/20 px-7 py-3.5 text-base font-bold text-white transition hover:bg-white/10 sm:w-auto"
          >
            Nhập mã trên tem
          </Link>
        </div>
      </section>
    </div>
  );
}
