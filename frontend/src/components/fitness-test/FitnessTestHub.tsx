"use client";

import Link from "next/link";
import BrandHero from "@/components/BrandHero";

export default function FitnessTestHub() {
  return (
    <div className="space-y-6">
      <BrandHero title="SỰ KIỆN">
        <p className="mt-6 text-sm leading-relaxed text-white/80 sm:text-base">
          Tham gia sự kiện đang diễn ra — camera nhận diện chống đẩy để nhận ưu đãi dụng cụ.
        </p>
      </BrandHero>

      <Link
        href="/sukien/giam-gia"
        className="block rounded-3xl bg-gradient-to-br from-orange-50 to-white p-6 shadow-soft ring-1 ring-orange-200 transition hover:ring-orange-400"
      >
        <p className="type-kicker text-orange-700">Sự kiện</p>
        <h2 className="mt-2 text-xl font-black text-slate-900">Sự kiện chống đẩy</h2>
        <p className="mt-2 text-sm text-slate-600">
          1 phút chống đẩy — camera nhận diện, nhận ưu đãi dụng cụ.
        </p>
        <span className="mt-4 inline-flex min-h-11 items-center rounded-xl bg-orange-600 px-4 py-2 text-sm font-bold text-white">
          Vào sự kiện
        </span>
      </Link>
    </div>
  );
}
