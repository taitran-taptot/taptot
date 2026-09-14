import Link from "next/link";
import Footer from "./Footer";
import BrandWordmark from "./BrandWordmark";
import TrainerRoster from "./TrainerRoster";
import { BRAND_NAME, BRAND_SLOGAN } from "@/lib/brand";
import { CONTACT_HREF } from "@/lib/trainers";

const MISSION_POINTS = [
  {
    title: "Lịch vừa sức",
    desc: "Bắt đầu từ nền tảng thật của bạn — không ép lịch 'pro', không đốt giai đoạn.",
  },
  {
    title: "Ăn món quen",
    desc: "Gợi ý từ cơm, thịt, rau — món Việt quen thuộc thay vì đếm gram xa lạ.",
  },
  {
    title: "HLV đồng hành",
    desc: "Khi bạn muốn người kèm riêng, đội PT collab với TAPTOT sẵn sàng bắt đầu cùng bạn.",
  },
];

export default function AboutPage() {
  return (
    <div className="space-y-12 pb-8">
      <header className="relative overflow-hidden rounded-3xl px-6 py-16 text-white shadow-soft sm:px-10 sm:py-20">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/hero-gym.jpg"
          alt=""
          aria-hidden
          className="absolute inset-0 h-full w-full object-cover object-center"
        />
        <div className="absolute inset-0 bg-[#0F172A]/75" />
        <div className="absolute inset-0 bg-brand-900/35" />
        <div className="relative max-w-2xl">
          <p className="text-sm font-semibold tracking-wide text-brand-300 uppercase">Về chúng tôi</p>
          <h1 className="mt-3 text-4xl font-extrabold tracking-tight sm:text-5xl">
            <BrandWordmark snow />
          </h1>
          <p className="mt-4 text-2xl font-extrabold tracking-tight sm:text-3xl">{BRAND_SLOGAN}</p>
          <p className="mt-3 max-w-xl text-base text-white/90 sm:text-lg">
            Mang lối sống lành mạnh đến cho bạn.
          </p>
        </div>
      </header>

      <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100 sm:p-10">
        <h2 className="text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">Sứ mệnh</h2>
        <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-600">
          {BRAND_NAME} giúp người Việt bắt đầu tập và ăn lành mạnh bằng công cụ rõ ràng: lịch vừa sức, kho bài tập,
          thực đơn quen thuộc, và huấn luyện viên đồng hành khi bạn cần người kèm.
        </p>
        <div className="mt-8 grid gap-8 sm:grid-cols-3 sm:gap-6">
          {MISSION_POINTS.map((m, i) => (
            <div
              key={m.title}
              className={i < MISSION_POINTS.length - 1 ? "sm:border-r sm:border-slate-100 sm:pr-6" : ""}
            >
              <h3 className="font-bold text-slate-900">{m.title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-slate-600">{m.desc}</p>
            </div>
          ))}
        </div>
        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/bat-dau"
            className="inline-flex items-center justify-center rounded-xl bg-brand-500 px-6 py-3 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
          >
            Bắt đầu
          </Link>
          <Link
            href={CONTACT_HREF}
            className="inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-6 py-3 text-sm font-bold text-slate-700 transition hover:border-brand-300 hover:text-brand-700"
          >
            Gặp HLV
          </Link>
        </div>
      </section>

      <TrainerRoster />

      <Footer />
    </div>
  );
}
