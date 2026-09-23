import Link from "next/link";
import BrandWordmark from "./BrandWordmark";
import HomeProductMockup from "./HomeProductMockup";
import RevealOnScroll from "./RevealOnScroll";

/** Placeholder — đổi ID khi có video chính thức (phần sau `watch?v=`). */
const EQUIPMENT_PROMO_YOUTUBE_ID = "EngW7tLk6R8";

const STEPS = [
  {
    n: "01",
    title: "Lộ trình",
    desc: "TAPTOT cung cấp kiến thức, lộ trình lịch tập và chế độ ăn linh hoạt phù hợp cho người mới từ con số 0.",
    href: "/batdau?moi=1",
    cta: "Xem lộ trình",
    visual: "bg-white",
    image: "/home-lo-trinh.png",
    alt: "Các bước trên lộ trình",
    fit: "object-contain p-6",
    flip: false,
  },
  {
    n: "02",
    title: "Dụng cụ",
    desc: "Dụng cụ của TAPTOT giúp buổi tập của bạn hiệu quả và đa dạng hơn.",
    href: "/mua-dung-cu",
    cta: "Mua dụng cụ",
    visual: "bg-slate-50",
    image: "/home-dung-cu.jpg",
    alt: "Dụng cụ tập luyện",
    fit: "object-cover object-center",
    flip: true,
  },
  {
    n: "03",
    title: "Huấn luyện viên",
    desc: "TAPTOT kết hợp cùng HLV chuyên nghiệp hỗ trợ bạn tiến tới những mục tiêu cao hơn, không chỉ đơn giản là khỏe hơn, đẹp hơn.",
    href: "/lien-he",
    cta: "Liên hệ HLV",
    visual: "bg-slate-100",
    image: "/home-hlv.png",
    alt: "Huấn luyện viên hướng dẫn buổi tập",
    fit: "object-cover object-center",
    flip: false,
  },
] as const;

const WHY = [
  {
    title: "Ăn món quen",
    desc: "Kho thực đơn đa dạng vùng miền trên khắp cả nước cho bạn lựa chọn.",
    href: "/thuc-an",
    cta: "Xem kho thực phẩm",
  },
  {
    title: "Vừa sức người mới",
    desc: "Cung cấp các bài tập tiên lợi đa dạng độ khó và ở mọi địa điểm giúp bạn linh hoạt tập luyện.",
    href: "/bai-tap",
    cta: "Kho bài tập",
  },
  {
    title: "Hiểu vì sao",
    desc: "Cung cấp kho kiến thức miễn phí để bạn có thể tự bắt đầu từ con số 0.",
    href: "/kien-thuc",
    cta: "Xem kho kiến thức",
  },
];

function StepVisual({ step }: { step: (typeof STEPS)[number] }) {
  const order = step.flip ? "lg:order-1" : "";
  return (
    <div
      className={`relative aspect-[4/3] min-h-[14rem] overflow-hidden rounded-2xl ${step.visual} ${order}`}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={step.image}
        alt={step.alt}
        className={`absolute inset-0 h-full w-full ${step.fit}`}
      />
    </div>
  );
}

export default function Landing() {
  return (
    <div className="space-y-14 pb-8 sm:space-y-16">
      <div className="space-y-5">
        <section className="home-product-hero relative isolate overflow-hidden rounded-[2rem] border border-slate-100 bg-[#FBFCFB] px-5 pb-8 pt-10 sm:px-9 sm:pb-10 sm:pt-14 lg:min-h-[520px] lg:px-14 lg:py-10">
          <div className="pointer-events-none absolute -left-24 top-20 -z-10 h-72 w-72 rounded-full bg-brand-50 blur-3xl" />
          <div className="pointer-events-none absolute -right-20 bottom-0 -z-10 h-80 w-80 rounded-full bg-emerald-50/80 blur-3xl" />
          <div className="grid items-center gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-4">
            <div className="home-hero-copy max-w-xl lg:py-10">
              <h1 className="type-display mt-0 max-w-md text-slate-800">
                <BrandWordmark />{" "}
                <span className="font-sans font-medium text-slate-700">
                  mang thói quen sống lành mạnh đến cho bạn.
                </span>
              </h1>
              <p className="mt-6 max-w-lg text-base leading-7 text-slate-600 sm:text-lg">
                Vì cộng đồng người Việt, chúng tôi cung cấp dịch vụ giúp bạn sống khỏe hơn mỗi ngày.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/batdau?moi=1"
                  className="inline-flex min-h-12 items-center justify-center rounded-full bg-brand-600 px-6 text-sm font-bold text-white shadow-[0_12px_28px_-14px_rgba(22,163,74,0.75)] transition hover:-translate-y-0.5 hover:bg-brand-700"
                >
                  Bắt đầu
                </Link>
                <Link
                  href="/ve-chung-toi"
                  className="inline-flex min-h-12 items-center justify-center rounded-full border border-slate-200 bg-white px-6 text-sm font-bold text-slate-700 transition hover:border-brand-300 hover:text-brand-700"
                >
                  Về TAPTOT
                </Link>
              </div>
            </div>
            <div className="home-hero-visual min-w-0">
              <HomeProductMockup />
            </div>
          </div>
        </section>

        <RevealOnScroll>
          <section className="relative overflow-hidden rounded-[2rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-8 shadow-soft sm:px-10 sm:py-10 lg:px-12">
            <div
              className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
              aria-hidden
            />
            <div className="relative grid items-center gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:gap-12">
              <div className="max-w-2xl">
                <h2 className="type-display text-slate-900">
                  Nhận lịch tập 100 ngày chỉ trong vài cú nhấp chuột.
                </h2>
                <Link
                  href="/mua-dung-cu?from=challenge"
                  className="mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-brand-400 sm:w-auto"
                >
                  Xem dụng cụ và nhận lịch tập
                </Link>
                <div className="mt-5 rounded-2xl border border-orange-200 bg-orange-50/70 px-5 py-4">
                  <p className="type-kicker inline-flex rounded-full bg-orange-500 px-3.5 py-1 text-white shadow-sm">
                    Sự kiện đặc biệt
                  </p>
                  <p className="mt-2 text-sm font-bold leading-relaxed text-orange-900 sm:text-base">
                    Thử sức với thử thách &ldquo;Chống đẩy càng nhiều -{" "}
                    <span className="font-serif italic font-semibold text-orange-600">Ưu đãi càng cao</span>
                    &rdquo; của chúng tôi.
                  </p>
                  <Link
                    href="/sukien/giam-gia"
                    className="mt-3 inline-flex min-h-11 w-full items-center justify-center rounded-xl border border-orange-300 bg-white px-5 py-2.5 text-sm font-bold text-orange-700 transition hover:bg-orange-100 sm:w-auto"
                  >
                    Thử sức ngay
                  </Link>
                </div>
              </div>

              <div>
                <div className="overflow-hidden rounded-2xl border border-brand-100 bg-white/90 shadow-sm">
                  <div className="relative aspect-video w-full bg-slate-900">
                    <iframe
                      className="absolute inset-0 h-full w-full"
                      src={`https://www.youtube-nocookie.com/embed/${EQUIPMENT_PROMO_YOUTUBE_ID}`}
                      title="Dụng cụ tập tại nhà, kèm lịch 100 ngày"
                      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                      allowFullScreen
                      loading="lazy"
                      referrerPolicy="strict-origin-when-cross-origin"
                    />
                  </div>
                </div>
                <p className="mt-2 text-center text-sm text-slate-500">
                  Dụng cụ tập tại nhà, kèm lịch 100 ngày
                </p>
              </div>
            </div>
          </section>
        </RevealOnScroll>

        <section className="rounded-[2rem] border border-slate-100 bg-white px-6 py-8 shadow-soft sm:px-10 sm:py-10">
          <div className="mb-6 text-center sm:mb-10">
            <h2 className="type-display text-slate-900">
              Dịch vụ của <BrandWordmark />
            </h2>
          </div>
          <ol className="space-y-8 sm:space-y-12">
            {STEPS.map((step, i) => (
              <li key={step.n}>
                <RevealOnScroll delayMs={i * 80}>
                  <div className="grid items-center gap-5 lg:grid-cols-2 lg:gap-10">
                    <div className={step.flip ? "lg:order-2" : undefined}>
                      <span className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-600 text-xs font-bold text-white">
                        {step.n}
                      </span>
                      <h3 className="mt-3 text-xl font-bold text-slate-900">{step.title}</h3>
                      <p className="mt-2 max-w-lg text-sm leading-relaxed text-slate-500 sm:text-base">
                        {step.desc}
                      </p>
                      <Link
                        href={step.href}
                        className="mt-4 inline-flex w-fit items-center gap-1.5 text-sm font-bold text-brand-700 transition hover:text-brand-800"
                      >
                        {step.cta}
                        <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                          <path d="M5 12h14M13 6l6 6-6 6" />
                        </svg>
                      </Link>
                    </div>
                    <StepVisual step={step} />
                  </div>
                </RevealOnScroll>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <section>
        <div className="mb-8 text-center">
          <h2 className="type-display">Vì sao chọn <BrandWordmark />?</h2>
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {WHY.map((w, i) => (
            <RevealOnScroll key={w.title} delayMs={i * 80} className="h-full">
              <Link
                href={w.href}
                className="group flex h-full flex-col rounded-2xl bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-1 hover:ring-brand-100"
              >
                <h3 className="font-bold text-slate-900 group-hover:text-brand-700">{w.title}</h3>
                <p className="mt-1 flex-1 text-sm leading-relaxed text-slate-500">{w.desc}</p>
                <span className="mt-4 inline-flex w-fit items-center gap-1.5 rounded-xl bg-brand-50 px-3.5 py-2 text-sm font-bold text-brand-700 transition group-hover:bg-brand-500 group-hover:text-white">
                  {w.cta}
                  <svg className="h-4 w-4 transition group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </span>
              </Link>
            </RevealOnScroll>
          ))}
        </div>
      </section>

      <RevealOnScroll>
        <section className="relative overflow-hidden rounded-[2rem] border border-brand-100 bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 text-center shadow-soft sm:px-10 sm:py-12">
          <div
            className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
            aria-hidden
          />
          <div className="relative mx-auto max-w-2xl">
            <h2 className="type-display text-slate-900">
              Chọn dụng cụ và bắt đầu với <BrandWordmark />
            </h2>
            <Link
              href="/mua-dung-cu?from=challenge"
              className="mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white transition hover:-translate-y-0.5 hover:bg-brand-400 sm:w-auto"
            >
              Xem dụng cụ và nhận lịch tập
            </Link>
          </div>
        </section>
      </RevealOnScroll>
    </div>
  );
}
