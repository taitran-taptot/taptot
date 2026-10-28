import Link from "next/link";
import BrandHero from "@/components/BrandHero";
import BrandWordmark from "@/components/BrandWordmark";

const SHOP_HREF = "/mua-dung-cu?from=challenge";
const GIFT_HREF = "/batdau?nhap-ma=1";

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
    title: "Lịch tập phù hợp thời gian biểu",
    desc: "Lịch tập cá nhân hóa với thời gian biểu của bạn, có video hướng dẫn tập và đi kèm giải thích dễ hiểu giúp bạn nhanh chóng làm quen.",
  },
  {
    title: "Lịch ăn phù hợp sở thích",
    desc: "Ăn chế độ nhưng không hề gò bó, bạn có thể chọn món ăn mình muốn ăn nhưng vẫn đạt được mục tiêu thay đổi vóc dáng.",
  },
];

const WHO = [
  "Muốn thay đổi vóc dáng bản thân nhưng chưa biết bắt đầu từ đâu.",
  "Muốn dáng đẹp nhưng vẫn muốn ăn linh hoạt, chế độ ăn không quá khắt khe.",
  "Muốn có một lịch trình rõ ràng phù hợp với địa điểm, mục tiêu và thời gian biểu cá nhân.",
];

export default function Challenge100Landing() {
  return (
    <div className="space-y-10">
      <BrandHero title="THỬ THÁCH 100 NGÀY" />

      <div className="space-y-10 rounded-3xl border border-slate-300 bg-white p-4 shadow-soft sm:p-6">
      <section>
        <h2 className="text-center type-title">Vì sao 100 ngày?</h2>
        <p className="mt-6 rounded-2xl bg-white p-5 text-center text-sm leading-relaxed text-slate-900 shadow-soft sm:p-6 sm:text-base">
          Vì 100 ngày là thời gian đủ dài để bạn tạo dựng thói quen lành mạnh và cũng là khoảng thời gian đủ để bạn
          thấy cơ thể thay đổi thành một phiên bản tốt hơn.
        </p>
      </section>

      <section>
        <h2 className="text-center type-title">Thử thách gồm những gì</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-3">
          {PHASES.map((p) => (
            <div key={p.n} className="rounded-2xl bg-white p-5 shadow-soft">
              <div className="flex items-center gap-3">
                <p className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                  {p.n}
                </p>
                <div className="min-w-0">
                  <p className="type-kicker text-brand-600">{p.weeks}</p>
                  <h3 className="mt-0.5 font-bold text-slate-900">{p.title}</h3>
                </div>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-slate-900">{p.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-center type-title">Bạn nhận được gì</h2>
        <div className="mt-6 grid gap-4 sm:grid-cols-2">
          {BENEFITS.map((b) => (
            <div key={b.title} className="rounded-2xl bg-white p-5 shadow-soft">
              <h3 className="font-bold text-slate-900">{b.title}</h3>
              <p className="mt-1 text-sm leading-relaxed text-slate-900">{b.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-center type-title">Ai hợp với thử thách này?</h2>
        <ul className="mt-6 space-y-2.5 rounded-2xl bg-white p-5 shadow-soft sm:p-6">
          {WHO.map((line) => (
            <li key={line} className="flex gap-2.5 text-sm leading-relaxed text-slate-900">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-brand-500" aria-hidden />
              {line}
            </li>
          ))}
        </ul>
      </section>
      </div>

      <section className="relative overflow-hidden rounded-[2rem] border border-brand-300 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 text-center shadow-soft sm:px-10 sm:py-12">
        <div
          className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
          aria-hidden
        />
        <div className="relative">
          <h2 className="type-display text-slate-900">
            Lộ trình được tặng cùng dụng cụ <BrandWordmark />
          </h2>
          <div className="mt-6 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href={SHOP_HREF}
              className="inline-flex w-full items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
            >
              Chọn dụng cụ
            </Link>
            <Link
              href={GIFT_HREF}
              className="inline-flex w-full items-center justify-center rounded-xl border border-slate-200 bg-white px-7 py-3.5 text-base font-bold text-slate-700 transition hover:border-brand-300 hover:text-brand-700 sm:w-auto"
            >
              Nhập mã trên tem
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
