import Link from "next/link";
import Footer from "./Footer";
import BrandWordmark from "./BrandWordmark";
import HomeProductMockup from "./HomeProductMockup";
import SmoothHashLink from "./SmoothHashLink";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";
import { equipmentImageFitClass, publicEquipmentImage } from "@/lib/equipmentCatalog";
import { mediaUrl } from "@/lib/labels";
import { CONTACT_HREF, FEATURED_TRAINER } from "@/lib/trainers";
import { HOME_SHOP_GROUPS } from "@/lib/shopMerchandising";

const CHALLENGE_HREF = "/thu-thach-100-ngay";

const PATHS = [
  {
    id: "coach",
    label: "Lựa chọn 1",
    title: "Tập cùng huấn luyện viên",
    desc: "Bạn có một mục tiêu lớn hơn không chỉ đơn giản tăng cân, giảm cân để giữ dáng?",
    cta: "Gặp HLV",
    href: "#hlv-dong-hanh",
    tone: "coach" as const,
  },
  {
    id: "challenge",
    label: "Lựa chọn 2",
    title: "Thử thách bản thân cùng TAPTOT",
    desc: "Bạn muốn thay đổi lối sống của bản thân từ điều nhỏ nhất?",
    cta: "Chấp nhận thử thách",
    href: "#thu-thach-100-ngay",
    tone: "challenge" as const,
  },
];

/** HLV spotlight — dữ liệu chung tại lib/trainers.ts */
const PT_SPOTLIGHT = {
  eyebrow: "HLV đồng hành",
  cta: "Bắt đầu hành trình",
  href: CONTACT_HREF,
  ...FEATURED_TRAINER,
};

/** Thử thách 100 ngày — ảnh bên phải; text bên trái (đối xứng với HLV). */
const CHALLENGE_SPOTLIGHT = {
  eyebrow: "Thử thách 100 ngày",
  title: "Thay đổi lối sống từ điều nhỏ nhất",
  role: "TAPTOT giúp bạn tạo thói quen lành mạnh.",
  bio: "Tập tốt, Ăn tốt, Sống tốt...Không ai xấu, không ai yếu, chỉ có người không dám quyết tâm thay đổi.",
  cta: "Thử thách 100 ngày với TAPTOT",
  href: CHALLENGE_HREF,
  imageSrc: "/challenge-100-cover.jpg",
  imageAlt: "Bắt đầu ngày đầu tiên của thử thách 100 ngày tại nhà",
};

const WHY = [
  {
    title: "Ăn món quen",
    desc: "Kho thực đơn đa dạng vùng miền trên khắp cả nước cho bạn lựa chọn.",
    href: "/kho-thuc-pham",
    cta: "Xem kho thực phẩm",
  },
  {
    title: "Vừa sức người mới",
    desc: "Cung cấp các bài tập tiên lợi đa dạng độ khó và ở mọi địa điểm giúp bạn linh hoạt tập luyện.",
    href: "/kho-bai-tap",
    cta: "Kho bài tập",
  },
  {
    title: "Hiểu vì sao",
    desc: "Cung cấp kho kiến thức miễn phí để bạn có thể tự bắt đầu thay đổi.",
    href: "/kien-thuc",
    cta: "Xem kho kiến thức",
  },
  {
    title: "Bắt đầu dễ dàng hơn",
    desc: "TAPTOT cung cấp các bài tập sử dụng đa dạng dụng cụ giúp bạn biết mình nên tập gì.",
    href: "/mua-dung-cu",
    cta: "Mua dụng cụ",
  },
];

export default function Landing() {
  return (
    <div className="space-y-14 pb-8 sm:space-y-16">
      <section className="home-product-hero relative isolate overflow-hidden rounded-[2rem] border border-slate-100 bg-[#FBFCFB] px-5 pb-8 pt-10 sm:px-9 sm:pb-10 sm:pt-14 lg:min-h-[650px] lg:px-14 lg:py-10">
        <div className="pointer-events-none absolute -left-24 top-20 -z-10 h-72 w-72 rounded-full bg-brand-50 blur-3xl" />
        <div className="pointer-events-none absolute -right-20 bottom-0 -z-10 h-80 w-80 rounded-full bg-emerald-50/80 blur-3xl" />
        <div className="grid items-center gap-8 lg:grid-cols-[0.9fr_1.1fr] lg:gap-4">
          <div className="home-hero-copy max-w-xl lg:py-10">
            <h1 className="mt-0 max-w-md text-2xl font-semibold leading-snug tracking-tight text-slate-800 sm:text-3xl sm:leading-snug lg:text-[2rem] lg:leading-[1.35]">
              <BrandWordmark className="font-extrabold tracking-tight" />{" "}
              <span className="font-medium text-slate-700">
                mang thói quen sống lành mạnh đến cho bạn.
              </span>
            </h1>
            <p className="mt-6 max-w-lg text-base leading-7 text-slate-600 sm:text-lg">
              Vì cộng đồng người Việt, chúng tôi cung cấp dịch vụ giúp bạn sống khỏe hơn mỗi ngày.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/bat-dau"
                className="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-brand-600 px-6 text-sm font-bold text-white shadow-[0_12px_28px_-14px_rgba(22,163,74,0.75)] transition hover:-translate-y-0.5 hover:bg-brand-700"
              >
                Bắt đầu
                <span aria-hidden>→</span>
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

      <section>
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Cách {BRAND_NAME} giúp bạn</h2>
        </div>
        <div className="relative grid gap-4 md:grid-cols-[1fr_auto_1fr] md:items-stretch md:gap-0">
          {PATHS.map((p, i) => (
            <div key={p.id} className="contents">
              {i === 1 && (
                <div className="hidden items-center justify-center px-3 md:flex" aria-hidden>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold tracking-wide text-slate-500 uppercase">
                    hoặc
                  </span>
                </div>
              )}
              <SmoothHashLink
                href={p.href}
                className={`group relative flex flex-col overflow-hidden rounded-3xl p-6 shadow-soft transition duration-200 hover:-translate-y-0.5 hover:shadow-lg sm:p-8 ${
                  p.tone === "coach"
                    ? "bg-white ring-1 ring-brand-100 hover:ring-brand-300"
                    : "bg-gradient-to-br from-orange-50 via-amber-50 to-orange-100 text-slate-900 ring-1 ring-orange-200 hover:ring-orange-300"
                }`}
              >
                <div
                  className={`pointer-events-none absolute inset-x-0 top-0 h-1 ${
                    p.tone === "coach" ? "bg-brand-500" : "bg-orange-400"
                  }`}
                />
                <p
                  className={`text-xs font-bold tracking-widest uppercase ${
                    p.tone === "coach" ? "text-brand-600" : "text-orange-600"
                  }`}
                >
                  {p.label}
                </p>
                <h3 className="mt-3 text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl">
                  {p.title}
                </h3>
                <p
                  className={`mt-3 flex-1 text-sm leading-relaxed sm:text-base ${
                    p.tone === "coach" ? "text-slate-500" : "text-slate-600"
                  }`}
                >
                  {p.desc}
                </p>
                <span
                  className={`mt-7 inline-flex w-fit items-center gap-2 rounded-xl px-5 py-3 text-sm font-bold transition ${
                    p.tone === "coach"
                      ? "bg-brand-500 text-white group-hover:bg-brand-600"
                      : "bg-orange-500 text-white group-hover:bg-orange-600"
                  }`}
                >
                  {p.cta}
                  <svg className="h-4 w-4 transition group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </span>
              </SmoothHashLink>
              {i === 0 && (
                <div className="flex items-center justify-center py-1 md:hidden" aria-hidden>
                  <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-bold tracking-wide text-slate-500 uppercase">
                    hoặc
                  </span>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      <section id="hlv-dong-hanh" className="scroll-mt-24 rounded-3xl bg-white p-6 shadow-soft sm:p-10">
        <div className="grid items-center gap-8 md:grid-cols-2 md:gap-10">
          <div className="relative mx-auto aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl bg-gradient-to-br from-brand-50 to-brand-100 md:mx-0 md:max-w-none">
            {PT_SPOTLIGHT.imageSrc ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={PT_SPOTLIGHT.imageSrc}
                alt={PT_SPOTLIGHT.name}
                className="absolute inset-0 h-full w-full object-cover object-top"
              />
            ) : (
              <div className="absolute inset-0 grid place-items-center" aria-hidden>
                <span className="text-5xl font-extrabold tracking-tight text-brand-600/40 sm:text-6xl">
                  {PT_SPOTLIGHT.initials}
                </span>
              </div>
            )}
          </div>
          <div>
            <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">
              {PT_SPOTLIGHT.eyebrow}
            </p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
              {PT_SPOTLIGHT.name}
            </h2>
            <p className="mt-1.5 text-sm font-medium text-slate-600">{PT_SPOTLIGHT.role}</p>
            <p className="mt-4 text-sm leading-relaxed text-slate-500 sm:text-base">
              {PT_SPOTLIGHT.bio}
            </p>
            <Link
              href={PT_SPOTLIGHT.href}
              className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
            >
              {PT_SPOTLIGHT.cta}
            </Link>
          </div>
        </div>
      </section>

      <section
        id="thu-thach-100-ngay"
        className="scroll-mt-24 rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 sm:p-10"
      >
        <div className="grid items-center gap-8 md:grid-cols-2 md:gap-10">
          <div className="order-2 md:order-1">
            <p className="text-sm font-semibold tracking-wide text-orange-600 uppercase">
              {CHALLENGE_SPOTLIGHT.eyebrow}
            </p>
            <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
              {CHALLENGE_SPOTLIGHT.title}
            </h2>
            <p className="mt-1.5 text-sm font-medium text-orange-700/80">{CHALLENGE_SPOTLIGHT.role}</p>
            <p className="mt-4 text-sm leading-relaxed text-slate-600 sm:text-base">
              {CHALLENGE_SPOTLIGHT.bio}
            </p>
            <Link
              href={CHALLENGE_SPOTLIGHT.href}
              className="mt-6 inline-flex w-full items-center justify-center rounded-xl bg-orange-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-orange-600 sm:w-auto"
            >
              {CHALLENGE_SPOTLIGHT.cta}
            </Link>
          </div>
          <div className="relative order-1 mx-auto aspect-[4/5] w-full max-w-sm overflow-hidden rounded-2xl ring-1 ring-slate-100 md:order-2 md:mx-0 md:max-w-none">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={CHALLENGE_SPOTLIGHT.imageSrc}
              alt={CHALLENGE_SPOTLIGHT.imageAlt}
              className="absolute inset-0 h-full w-full object-cover object-center"
            />
          </div>
        </div>
      </section>

      <section className="overflow-hidden rounded-3xl bg-gradient-to-b from-slate-50 to-white shadow-soft ring-1 ring-slate-100">
        <div className="flex flex-col gap-5 px-6 pt-8 pb-2 sm:flex-row sm:items-end sm:justify-between sm:px-10 sm:pb-1">
          <div className="max-w-2xl">
            <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">
              Dụng cụ để bắt đầu ngay tại nhà của mình
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-slate-500 sm:text-base">
              Mỗi dụng cụ TAPTOT đều được tặng kèm lộ trình 100 ngày, gồm lịch tập tại nhà và lịch ăn theo thể trạng của bạn.
            </p>
          </div>
          <Link
            href="/mua-dung-cu?from=challenge"
            className="inline-flex min-h-11 shrink-0 items-center justify-center rounded-xl bg-brand-500 px-5 py-3 text-sm font-bold text-white transition hover:bg-brand-600"
          >
            Chọn dụng cụ · Nhận lộ trình
          </Link>
        </div>

        <div className="flex flex-col gap-3 p-4 sm:gap-4 sm:p-6 md:grid md:grid-cols-3">
          {HOME_SHOP_GROUPS.map((group) => {
            const dual = group.products.length >= 2;
            return (
              <Link
                key={group.id}
                href={group.href}
                className={`group relative flex items-center gap-3 overflow-hidden rounded-2xl border px-3 py-3.5 transition duration-200 sm:px-4 sm:py-5 ${group.homeSurface} ${group.homeHover}`}
              >
                <span className={`absolute inset-y-0 left-0 w-1.5 ${group.accentBar}`} aria-hidden />
                {dual ? (
                  <span
                    className={`flex h-[4.5rem] w-[6.75rem] shrink-0 items-center gap-1 rounded-xl bg-white/80 p-1 ring-1 transition duration-200 group-hover:scale-[1.03] group-hover:bg-white sm:h-20 sm:w-[7.25rem] ${group.tint}`}
                  >
                    {group.products.map((product, idx) => {
                      const path = publicEquipmentImage(product.slug);
                      const src = path ? mediaUrl(path) : null;
                      return (
                        <span key={product.slug} className="contents">
                          {idx > 0 && (
                            <span className="text-[10px] font-bold text-slate-400" aria-hidden>
                              +
                            </span>
                          )}
                          <span className="grid h-full flex-1 place-items-center rounded-lg bg-white/90">
                            {src ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={src}
                                alt={product.label_vi}
                                className={`max-h-[90%] max-w-[90%] ${
                                  product.slug === "gymnastic-rings"
                                    ? equipmentImageFitClass(product.slug)
                                    : "object-contain"
                                }`}
                              />
                            ) : (
                              <span className="text-[10px] text-slate-400">—</span>
                            )}
                          </span>
                        </span>
                      );
                    })}
                  </span>
                ) : (
                  <span
                    className={`grid h-[4.5rem] w-[4.5rem] shrink-0 place-items-center rounded-xl bg-white/80 ring-1 transition duration-200 group-hover:scale-[1.03] group-hover:bg-white sm:h-20 sm:w-20 ${group.tint}`}
                  >
                    {(() => {
                      const path = publicEquipmentImage(group.products[0]?.slug);
                      const src = path ? mediaUrl(path) : null;
                      return src ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img
                          src={src}
                          alt=""
                          className="max-h-[88%] max-w-[88%] object-contain"
                        />
                      ) : (
                        <span className="text-xs text-slate-400">—</span>
                      );
                    })()}
                  </span>
                )}
                <span className="min-w-0 flex-1 pr-1">
                  <span className={`badge ${group.badge}`}>{group.difficulty}</span>
                  <span className="mt-1.5 block text-[15px] font-bold leading-snug text-slate-900">
                    {group.label_vi}
                  </span>
                  <span className="mt-0.5 block text-xs leading-relaxed text-slate-600">
                    {group.hint}
                  </span>
                </span>
                <span
                  className={`grid h-9 w-9 shrink-0 place-items-center rounded-full bg-white/90 text-sm font-bold shadow-sm ring-1 ring-black/5 transition duration-200 group-hover:translate-x-0.5 ${group.homeArrow}`}
                  aria-hidden
                >
                  →
                </span>
              </Link>
            );
          })}
        </div>
      </section>

      <section>
        <div className="mb-8 text-center">
          <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">Vì sao chọn {BRAND_NAME}?</h2>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {WHY.map((w) => (
            <Link
              key={w.title}
              href={w.href}
              className="group flex flex-col rounded-2xl bg-white p-5 shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg hover:ring-1 hover:ring-brand-100"
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
          ))}
        </div>
      </section>

      <section className="relative overflow-hidden rounded-3xl px-6 py-14 text-center text-white shadow-soft sm:px-10 sm:py-20">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero-gym.jpg"
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-[#0F172A]/75" />
        <div className="absolute inset-0 bg-brand-900/35" />
        <div className="relative mx-auto max-w-3xl">
          <p className="text-3xl font-extrabold tracking-tight sm:text-5xl">
            <BrandWordmark snow />
          </p>
          <h2 className="mt-4 text-2xl font-extrabold tracking-tight sm:text-4xl">
            {BRAND_SLOGAN}
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-base text-white/90 sm:text-lg">
            Mang lối sống lành mạnh đến cho bạn.
          </p>
          <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
            <Link
              href={CONTACT_HREF}
              className="w-full rounded-xl bg-brand-500 px-7 py-3.5 text-base font-bold text-white shadow-soft transition hover:bg-brand-600 sm:w-auto"
            >
              Bắt đầu hành trình
            </Link>
            <Link
              href={CHALLENGE_HREF}
              className="w-full rounded-xl bg-white px-7 py-3.5 text-base font-bold text-brand-700 shadow-soft transition hover:bg-brand-50 sm:w-auto"
            >
              Thử thách 100 ngày
            </Link>
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}
