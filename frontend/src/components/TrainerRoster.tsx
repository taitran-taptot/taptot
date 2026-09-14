"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  CONTACT_HREF,
  TRAINER_REGIONS,
  TRAINERS,
  type TrainerRegion,
} from "@/lib/trainers";

export default function TrainerRoster() {
  const [region, setRegion] = useState<TrainerRegion | "all">("all");
  const list = useMemo(
    () => (region === "all" ? TRAINERS : TRAINERS.filter((t) => t.region === region)),
    [region],
  );

  return (
    <section>
      <div className="mb-6">
        <p className="text-sm font-semibold tracking-wide text-brand-600 uppercase">Đội hình</p>
        <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900 sm:text-3xl">
          Huấn luyện viên
        </h2>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-slate-600 sm:text-base">
          PT collab theo vùng miền — tập cùng người thật, không chỉ lịch trên màn hình.
        </p>
        <p className="mt-2 text-xs text-slate-400">Hồ sơ minh họa, sẽ thay bằng HLV thật.</p>
      </div>

      <div className="mb-8 flex flex-wrap gap-2">
        {TRAINER_REGIONS.map((r) => {
          const active = region === r.id;
          return (
            <button
              key={r.id}
              type="button"
              onClick={() => setRegion(r.id)}
              className={`rounded-full px-4 py-2 text-sm font-bold transition ${
                active
                  ? "bg-brand-500 text-white shadow-soft"
                  : "bg-white text-slate-600 ring-1 ring-slate-200 hover:ring-brand-300 hover:text-brand-700"
              }`}
            >
              {r.label}
            </button>
          );
        })}
      </div>

      <div className="space-y-10 sm:space-y-14">
        {list.map((t, i) => {
          const flip = i % 2 === 1;
          return (
            <article
              key={t.id}
              className={`flex flex-col items-center gap-6 sm:gap-10 ${
                flip ? "sm:flex-row-reverse" : "sm:flex-row"
              }`}
            >
              <div className={`relative shrink-0 ${flip ? "sm:translate-y-4" : "sm:-translate-y-2"}`}>
                <div className="h-44 w-44 overflow-hidden rounded-full bg-gradient-to-br from-brand-50 to-brand-100 shadow-soft ring-4 ring-white sm:h-56 sm:w-56">
                  {t.imageSrc ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={t.imageSrc} alt={t.name} className="h-full w-full object-cover object-top" />
                  ) : (
                    <div className="grid h-full place-items-center" aria-hidden>
                      <span className="text-4xl font-extrabold tracking-tight text-brand-600/40">
                        {t.initials}
                      </span>
                    </div>
                  )}
                </div>
                <span className="absolute bottom-2 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-full bg-slate-900 px-3 py-1 text-[11px] font-bold text-white shadow-soft sm:bottom-3">
                  {t.regionLabel}
                </span>
              </div>
              <div className={`max-w-md flex-1 text-center ${flip ? "sm:text-right" : "sm:text-left"}`}>
                <h3 className="text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl">{t.name}</h3>
                <p className="mt-1 text-sm font-medium text-slate-600">{t.role}</p>
                <p className="mt-0.5 text-sm text-slate-500">
                  {t.city} · {t.regionLabel}
                </p>
                <p className="mt-3 text-sm leading-relaxed text-slate-500">{t.bio}</p>
                <Link
                  href={CONTACT_HREF}
                  className={`mt-5 inline-flex items-center justify-center rounded-xl bg-brand-500 px-5 py-2.5 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600 ${
                    flip ? "sm:ml-auto" : ""
                  }`}
                >
                  Gặp HLV
                </Link>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
