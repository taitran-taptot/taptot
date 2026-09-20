"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Modal from "@/components/Modal";
import { formatGiftCodeInput } from "@/lib/giftCode";
import { redeemCodeApi } from "@/lib/shopApi";
import type { ChallengeOfferKey, GenderKey } from "@/lib/fitness-tracker";
import { clearFitnessTestReturnPath, isAdvancedFitnessTest } from "@/lib/fitness-tracker";
import {
  FITNESS_TEST_GUEST_SLUG,
  FITNESS_TEST_PACKAGES,
  isChallengeOfferKey,
  isGenderKey,
  offerRequiresProductCode,
} from "@/lib/fitness-tracker/session/offers";

function normalizePresetOffer(raw?: string): ChallengeOfferKey | null {
  if (!isChallengeOfferKey(raw)) return null;
  return isAdvancedFitnessTest(raw) ? "fitness_advanced" : raw;
}

export default function FitnessTestHub({
  presetCode,
  presetOffer,
  presetGender,
}: {
  presetCode?: string;
  presetOffer?: string;
  presetGender?: string;
}) {
  const router = useRouter();
  const [open, setOpen] = useState<ChallengeOfferKey | null>(normalizePresetOffer(presetOffer));
  const [code, setCode] = useState(presetCode ? formatGiftCodeInput(presetCode) : "");
  const [gender, setGender] = useState<GenderKey>(isGenderKey(presetGender) ? presetGender : "male");
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);

  const packages = useMemo(() => FITNESS_TEST_PACKAGES, []);

  async function confirm() {
    if (!open) return;
    clearFitnessTestReturnPath();
    const qs = new URLSearchParams({ goi: open, gender });
    if (!offerRequiresProductCode(open)) {
      router.push(`/kiemtratheluc/${FITNESS_TEST_GUEST_SLUG}?${qs.toString()}`);
      return;
    }
    const formatted = formatGiftCodeInput(code);
    if (formatted.replace(/-/g, "").length < 10) {
      setError("Nhập đủ mã trên tem, dạng TT-XXXX-XXXX.");
      return;
    }
    setChecking(true);
    setError("");
    try {
      const result = await redeemCodeApi.lookup(formatted);
      if (!result.valid) {
        setError("Mã đã dùng hoặc không đúng. Kiểm tra tem trên sản phẩm đã ship.");
        return;
      }
      router.push(`/kiemtratheluc/${encodeURIComponent(formatted)}?${qs.toString()}`);
    } catch {
      setError("Không kiểm tra được mã. Thử lại sau.");
    } finally {
      setChecking(false);
    }
  }

  return (
    <div className="space-y-8">
      <header className="rounded-3xl bg-gradient-to-br from-orange-50 via-white to-brand-50 px-6 py-10 shadow-soft ring-1 ring-orange-100 sm:px-10">
        <p className="text-sm font-semibold tracking-wide text-orange-600 uppercase">Kiểm tra thể lực</p>
        <h1 className="mt-2 text-3xl font-extrabold tracking-tight text-slate-900 sm:text-4xl">
          Chọn gói thử thách rồi test bằng camera
        </h1>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 sm:text-base">
          Cửa ra nền tảng nâng cao là đầu vào thử thách 12 tuần. Test chính thức chỉ vào ngày tốt nghiệp.
          Gói 100 ngày và cửa ra đang mở thử, không cần mã tem. Pose chạy trên máy bạn — không gửi video lên server.
        </p>
      </header>

      <div className="grid gap-5 lg:grid-cols-3">
        {packages.map((pkg) => (
            <button
              key={pkg.key}
              type="button"
              onClick={() => {
                setOpen(pkg.key);
                setError("");
              }}
              className="flex flex-col rounded-3xl bg-white p-6 text-left shadow-soft ring-1 ring-slate-100 transition hover:ring-brand-300"
            >
              <span className="text-xs font-bold tracking-wide text-brand-600 uppercase">
                {pkg.kicker}
              </span>
              <span className="mt-2 text-xl font-extrabold text-slate-900">{pkg.label_vi}</span>
              <span className="mt-2 text-sm leading-relaxed text-slate-600">
                {pkg.intro}
              </span>
              <span className="mt-4 text-sm font-bold text-brand-700">Chọn gói này →</span>
            </button>
        ))}
      </div>

      <Link
        href="/kiemtratheluc/giam-gia"
        className="flex flex-col rounded-3xl bg-gradient-to-br from-amber-50 to-orange-100 p-6 shadow-soft ring-1 ring-orange-200"
      >
        <span className="text-xs font-bold tracking-wide text-orange-600 uppercase">Phụ kiện</span>
        <span className="mt-1 text-xl font-extrabold text-slate-900">Chống đẩy 1 phút · giảm giá dụng cụ</span>
        <span className="mt-2 text-sm text-slate-600">
          0–20 cái: 5% · 21–50 cái: 7% · trên 50 cái: 10%. Camera đếm rep, không cần mã sản phẩm.
        </span>
      </Link>

      <Modal
        open={!!open}
        onClose={() => setOpen(null)}
        title={open && !offerRequiresProductCode(open) ? "Chọn giới tính" : "Nhập mã sản phẩm"}
      >
        <div className="space-y-4 p-5">
          <h2 className="text-lg font-extrabold">
            {open && !offerRequiresProductCode(open) ? "Chọn giới tính rồi vào test" : "Nhập mã tem và giới tính"}
          </h2>
          {open && !offerRequiresProductCode(open) ? (
            <p className="text-sm text-slate-600">
              {open === "advanced_foundation"
                ? "Cửa ra nền tảng nâng cao đang mở thử — không cần mã tem. Đây là đầu vào thử thách thể lực nâng cao."
                : "Gói 100 ngày đang mở thử — tạm thời không cần mã tem. Chọn Nam hoặc Nữ rồi bắt đầu."}
            </p>
          ) : (
            <p className="text-sm text-slate-600">
              Mã được in cùng QR trên sản phẩm đã ship. Chưa dùng mã lúc này — mã chỉ bị khóa khi bạn tạo lịch.
            </p>
          )}
          {open && offerRequiresProductCode(open) ? (
            <label className="block text-sm font-semibold text-slate-700">
              Mã sản phẩm
              <input
                className="field mt-1 uppercase"
                value={code}
                onChange={(e) => setCode(formatGiftCodeInput(e.target.value))}
                placeholder="TT-XXXX-XXXX"
                autoComplete="off"
              />
            </label>
          ) : null}
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
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <button
            type="button"
            disabled={checking}
            className="w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white disabled:opacity-50"
            onClick={() => void confirm()}
          >
            {checking ? "Đang kiểm tra mã…" : "Vào bài test"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
