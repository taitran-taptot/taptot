"use client";

import Link from "next/link";
import BrandHero from "@/components/BrandHero";

type EventCard = {
  href: string;
  title: string;
  summary: string;
  duration: string;
  format: string;
  reward: string;
  rewardDetail: string;
  tone: "orange" | "emerald";
};

const EVENTS: EventCard[] = [
  {
    href: "/sukien/chongday-giamgia",
    title: "Chống đẩy giảm giá",
    summary: "Chống đẩy càng nhiều trong 1 phút, mức giảm khi mua dụng cụ càng cao.",
    duration: "15 giây chuẩn bị, rồi 1 phút",
    format: "Ngay trên website",
    reward: "Tùy theo sức của bạn",
    rewardDetail: "Bạn làm càng nhiều giảm giá càng cao",
    tone: "orange",
  },
  {
    href: "/sukien/plank-giamgia",
    title: "Plank giảm giá",
    summary: "Giữ plank đủ 1 phút để nhận ưu đãi cố định khi mua dụng cụ.",
    duration: "15 giây chuẩn bị, rồi 1 phút",
    format: "Ngay trên website",
    reward: "Giảm 10%",
    rewardDetail: "Giữ đủ 1 phút. Vỡ form liên tục 5 giây thì thử thách dừng.",
    tone: "emerald",
  },
];

const TONE = {
  orange: {
    banner: "bg-gradient-to-br from-orange-500 via-orange-600 to-orange-700",
    reward: "bg-orange-50 text-orange-950 ring-orange-100",
    button: "bg-orange-600 group-hover:bg-orange-700",
  },
  emerald: {
    banner: "bg-gradient-to-br from-emerald-500 via-emerald-600 to-emerald-800",
    reward: "bg-emerald-50 text-emerald-950 ring-emerald-100",
    button: "bg-emerald-600 group-hover:bg-emerald-700",
  },
} as const;

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[11px] font-bold uppercase tracking-wide text-slate-400">{label}</p>
      <p className="mt-1 text-sm font-semibold leading-snug text-slate-800">{value}</p>
    </div>
  );
}

export default function FitnessTestHub() {
  return (
    <div className="space-y-6">
      <BrandHero title="SỰ KIỆN" />

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 sm:gap-5">
        {EVENTS.map((event) => {
          const tone = TONE[event.tone];
          return (
            <Link
              key={event.href}
              href={event.href}
              className="group flex h-full flex-col overflow-hidden rounded-3xl bg-white shadow-soft ring-1 ring-slate-200 transition hover:-translate-y-0.5 hover:shadow-md"
            >
              <div className={`relative px-5 py-5 text-white sm:px-6 sm:py-6 ${tone.banner}`}>
                <div className="flex items-center justify-between gap-3">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-white/20 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wide">
                    <span className="h-1.5 w-1.5 rounded-full bg-white" aria-hidden />
                    Đang diễn ra
                  </span>
                  <span className="text-xs font-semibold text-white/85">Tại nhà</span>
                </div>
                <h2 className="mt-4 text-2xl font-black leading-tight">{event.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-white/90">{event.summary}</p>
              </div>

              <div className="flex flex-1 flex-col gap-4 px-5 py-5 sm:px-6">
                <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <Fact label="Thời lượng" value={event.duration} />
                  <Fact label="Cách tham gia" value={event.format} />
                </div>
                <div className={`rounded-2xl px-4 py-3 ring-1 ${tone.reward}`}>
                  <p className="text-[11px] font-bold uppercase tracking-wide opacity-70">Phần thưởng</p>
                  <p className="mt-1 text-lg font-black leading-none">{event.reward}</p>
                  <p className="mt-2 text-sm leading-relaxed">{event.rewardDetail}</p>
                </div>
                <span
                  className={`mt-auto inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2.5 text-sm font-bold text-white transition ${tone.button}`}
                >
                  Tham gia ngay
                  <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} aria-hidden>
                    <path d="M5 12h14M13 6l6 6-6 6" />
                  </svg>
                </span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
