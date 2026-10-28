"use client";

import Link from "next/link";
import BrandHero from "@/components/BrandHero";

export default function FitnessTestHub() {
  return (
    <div className="space-y-6">
      <BrandHero title="SỰ KIỆN" />

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
        <Link
          href="/sukien/chongday-giamgia"
          className="flex h-full flex-col rounded-3xl bg-gradient-to-br from-orange-50 to-white p-4 shadow-soft ring-1 ring-orange-300 transition hover:ring-orange-400 sm:p-6"
        >
          <p className="type-kicker text-orange-700">Sự kiện</p>
          <h2 className="mt-2 text-lg font-black text-slate-900 sm:text-xl">Sự kiện chống đẩy</h2>
          <p className="mt-2 text-sm text-slate-600">
            1 phút chống đẩy - làm càng nhiều ưu đãi càng cao
          </p>
          <span className="mt-4 inline-flex min-h-11 items-center self-start rounded-xl bg-orange-600 px-4 py-2 text-sm font-bold text-white">
            Tham gia
          </span>
        </Link>

        <Link
          href="/sukien/plank-giamgia"
          className="flex h-full flex-col rounded-3xl bg-gradient-to-br from-emerald-50 to-white p-4 shadow-soft ring-1 ring-emerald-300 transition hover:ring-emerald-400 sm:p-6"
        >
          <p className="type-kicker text-emerald-700">Sự kiện</p>
          <h2 className="mt-2 text-lg font-black text-slate-900 sm:text-xl">Sự kiện plank</h2>
          <p className="mt-2 text-sm text-slate-600">
            1 phút plank - hoàn thành nhận ưu đãi giảm giá 10%
          </p>
          <span className="mt-4 inline-flex min-h-11 items-center self-start rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white">
            Tham gia
          </span>
        </Link>
      </div>
    </div>
  );
}
