"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import BrandWordmark from "@/components/BrandWordmark";
import Modal from "@/components/Modal";
import type { ChallengeOfferKey, GenderKey } from "@/lib/fitness-tracker";
import { clearFitnessTestReturnPath } from "@/lib/fitness-tracker";
import {
  FITNESS_TEST_GUEST_SLUG,
  FITNESS_TEST_PACKAGES,
  isChallengeOfferKey,
  isGenderKey,
} from "@/lib/fitness-tracker/session/offers";

function normalizePresetOffer(raw?: string): ChallengeOfferKey | null {
  return isChallengeOfferKey(raw) ? raw : null;
}

const PACKAGE_CARD_UI: Record<
  "challenge_100" | "advanced_foundation",
  { card: string; stripe: string; kicker: string; cta: string }
> = {
  challenge_100: {
    card: "bg-gradient-to-br from-brand-50 to-white ring-brand-100 hover:ring-brand-300",
    stripe: "bg-brand-400",
    kicker: "badge badge-easy",
    cta: "text-brand-700",
  },
  advanced_foundation: {
    card: "bg-gradient-to-br from-emerald-50 to-brand-50 ring-emerald-200 hover:ring-emerald-400",
    stripe: "bg-emerald-700",
    kicker: "badge bg-emerald-100 text-emerald-800",
    cta: "text-emerald-800",
  },
};

export default function FitnessTestHub({
  presetOffer,
  presetGender,
}: {
  presetCode?: string;
  presetOffer?: string;
  presetGender?: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState<ChallengeOfferKey | null>(normalizePresetOffer(presetOffer));
  const [gender, setGender] = useState<GenderKey>(isGenderKey(presetGender) ? presetGender : "male");

  const packages = useMemo(() => FITNESS_TEST_PACKAGES, []);

  function confirm() {
    if (!open) return;
    clearFitnessTestReturnPath();
    const qs = new URLSearchParams({ goi: open, gender });
    router.push(`/kiemtratheluc/${FITNESS_TEST_GUEST_SLUG}?${qs.toString()}`);
  }

  return (
    <div className="space-y-8">
      <header className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-10 shadow-soft ring-1 ring-brand-100 sm:px-10">
        <div
          className="pointer-events-none absolute -right-16 -top-28 h-72 w-72 rounded-full bg-brand-200/45 blur-3xl"
          aria-hidden
        />
        <div
          className="pointer-events-none absolute -left-20 -bottom-24 h-56 w-56 rounded-full bg-emerald-200/35 blur-3xl"
          aria-hidden
        />
        <div className="relative">
          <h1 className="type-display text-slate-900">
            Kiểm tra thể lực với <BrandWordmark />
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
            TAPTOT chuẩn bị các tiêu chuẩn thể lực để kiểm tra đầu vào nhằm biết người tập có phù hợp
            với thử thách tương ứng hay không.
          </p>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-3">
        {packages.map((pkg) => {
          const ui = PACKAGE_CARD_UI[pkg.key as keyof typeof PACKAGE_CARD_UI];
          return (
            <button
              key={pkg.key}
              type="button"
              onClick={() => setOpen(pkg.key)}
              className={`relative flex flex-col overflow-hidden rounded-3xl p-6 pt-7 text-left shadow-soft ring-1 transition ${ui.card}`}
            >
              <span className={`absolute inset-x-0 top-0 h-1.5 ${ui.stripe}`} aria-hidden />
              <span className={`self-start ${ui.kicker}`}>{pkg.kicker}</span>
              <span className="mt-2 type-title text-slate-900">{pkg.label_vi}</span>
              <span className={`mt-4 text-sm font-bold ${ui.cta}`}>Kiểm tra →</span>
            </button>
          );
        })}
        <Link
          href="/kiemtratheluc/giam-gia"
          className="relative flex flex-col overflow-hidden rounded-3xl bg-gradient-to-br from-accent-50 to-accent-100 p-6 pt-7 shadow-soft ring-1 ring-accent-200 transition hover:ring-accent-400"
        >
          <span className="absolute inset-x-0 top-0 h-1.5 bg-accent-500" aria-hidden />
          <span className="badge badge-new self-start">Sự kiện</span>
          <span className="mt-2 type-title text-slate-900">Chống đẩy · giảm giá dụng cụ</span>
          <span className="mt-4 text-sm font-bold text-accent-700">Kiểm tra →</span>
        </Link>
      </div>

      <Modal open={!!open} onClose={() => setOpen(null)} title="Chọn giới tính">
        <div className="space-y-4 p-5">
          <h2 className="text-lg font-bold">Chọn giới tính rồi vào test</h2>
          <p className="text-sm text-slate-600">
            {open === "advanced_foundation"
              ? "Cửa ra nền tảng đang mở thử — không cần mã tem. Đây là đầu vào thử thách 12 tuần."
              : "Gói 100 ngày đang mở thử — không cần mã tem. Chọn Nam hoặc Nữ rồi bắt đầu."}
          </p>
          <div className="flex gap-2">
            {(["male", "female"] as const).map((g) => (
              <button
                key={g}
                type="button"
                onClick={() => setGender(g)}
                className={`flex-1 rounded-xl border px-3 py-2.5 text-sm font-bold ${
                  gender === g ? "border-brand-500 bg-brand-500 text-white" : "border-slate-200"
                }`}
              >
                {g === "male" ? "Nam" : "Nữ"}
              </button>
            ))}
          </div>
          <button
            type="button"
            className="w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white"
            onClick={confirm}
          >
            Vào bài test
          </button>
        </div>
      </Modal>
    </div>
  );
}
