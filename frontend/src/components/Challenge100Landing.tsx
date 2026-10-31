import Link from "next/link";
import BrandHero from "@/components/BrandHero";
import BrandWordmark from "@/components/BrandWordmark";
import RevealOnScroll from "@/components/RevealOnScroll";

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
    <div className="space-y-16 sm:space-y-20">
      <BrandHero title="THỬ THÁCH 100 NGÀY" />

      <RevealOnScroll>
        <section className="mx-auto max-w-3xl px-2 text-center">
          <h2 className="type-title">Vì sao 100 ngày?</h2>
          <p className="mt-5 text-lg leading-relaxed text-slate-800 sm:text-xl">
            Vì 100 ngày là thời gian đủ dài để bạn tạo dựng thói quen lành mạnh và cũng là khoảng thời gian đủ để bạn
            thấy cơ thể thay đổi thành một phiên bản tốt hơn.
          </p>
        </section>
      </RevealOnScroll>

      <section>
        <RevealOnScroll>
          <h2 className="text-center type-title">Thử thách gồm những gì</h2>
        </RevealOnScroll>
        <div className="relative mt-8">
          <span
            className="pointer-events-none absolute left-[16%] right-[16%] top-[1.125rem] hidden h-px bg-brand-200 sm:block"
            aria-hidden
          />
        <ol className="grid gap-8 sm:grid-cols-3 sm:gap-6">
          {PHASES.map((phase, index) => (
            <li key={phase.n} className="relative">
              <RevealOnScroll delayMs={index * 80}>
                <div className="flex items-start gap-3 sm:flex-col sm:items-center sm:text-center">
                  <p className="relative z-10 grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-600 text-sm font-bold text-white">
                    {phase.n}
                  </p>
                  <div className="min-w-0">
                    <p className="type-kicker text-brand-600">{phase.weeks}</p>
                    <h3 className="mt-0.5 font-bold text-slate-900">{phase.title}</h3>
                    <p className="mt-2 text-sm leading-relaxed text-slate-700">{phase.desc}</p>
                  </div>
                </div>
              </RevealOnScroll>
            </li>
          ))}
        </ol>
        </div>
      </section>

      <section>
        <RevealOnScroll>
          <h2 className="text-center type-title">Bạn nhận được gì</h2>
        </RevealOnScroll>
        <div className="mt-8 grid gap-4 sm:grid-cols-2">
          {BENEFITS.map((benefit, index) => (
            <RevealOnScroll key={benefit.title} delayMs={index * 80}>
              <div className="h-full rounded-3xl border border-brand-100 bg-brand-50 p-6 sm:p-8">
                <h3 className="text-lg font-bold text-slate-900">{benefit.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-700 sm:text-base">{benefit.desc}</p>
              </div>
            </RevealOnScroll>
          ))}
        </div>
      </section>

      <section>
        <RevealOnScroll>
          <h2 className="text-center type-title">Ai hợp với thử thách này?</h2>
        </RevealOnScroll>
        <ul className="mt-8 grid gap-3 sm:grid-cols-3">
          {WHO.map((line, index) => (
            <li key={line}>
              <RevealOnScroll delayMs={index * 80}>
                <p className="h-full rounded-2xl border border-slate-200 bg-white p-5 text-sm leading-relaxed text-slate-800">
                  {line}
                </p>
              </RevealOnScroll>
            </li>
          ))}
        </ul>
      </section>

      <RevealOnScroll>
        <section className="relative overflow-hidden rounded-[2rem] border border-brand-300 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 text-center shadow-soft sm:px-10 sm:py-12">
          <div
            className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
            aria-hidden
          />
          <div className="relative">
            <h2 className="type-display text-slate-900">
              Bắt đầu thử thách ngay cùng <BrandWordmark />
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
      </RevealOnScroll>
    </div>
  );
}
