"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Modal from "@/components/Modal";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";
import FitnessTestSession from "@/components/fitness-test/FitnessTestSession";
import { aiApi, type FamiliarizationCatalog } from "@/lib/authApi";
import { TERMS_HREF } from "@/lib/terms";
import { FITNESS_TEST_GUEST_SLUG, offerLabel } from "@/lib/fitness-tracker/session/offers";
import {
  builderPathAfterFitnessTest,
  FITNESS_TEST_FROM_BUILDER,
  fitnessTestReturnPath,
  isFitnessTestFromBuilder,
  isFoundationExitTest,
  offerIncludesRun,
  offerStandardLevel,
} from "@/lib/fitness-tracker";
import type { ChallengeOfferKey, GenderKey } from "@/lib/fitness-tracker";

const FALLBACK_STANDARDS: FamiliarizationCatalog["standards"] = {
  male: {
    basic: [
      { key: "push", label_vi: "Chống đẩy", display_vi: "8–15 lần sàn" },
      { key: "pull", label_vi: "Kéo", display_vi: "2–6 kéo xà hoặc kéo người nằm (bàn/xà)" },
      { key: "squat", label_vi: "Squat thể trọng", display_vi: "20–35 lần" },
      { key: "plank", label_vi: "Plank", display_vi: "45–75 giây" },
      { key: "run", label_vi: "Đi bộ/chạy 10 phút", display_vi: "1,1–1,5 km" },
    ],
    advanced: [
      { key: "push", label_vi: "Chống đẩy", display_vi: "12–25 lần sàn" },
      { key: "pull", label_vi: "Kéo", display_vi: "4–10 kéo xà hoặc kéo người nằm thấp" },
      { key: "squat", label_vi: "Squat thể trọng", display_vi: "25–45 lần" },
      { key: "plank", label_vi: "Plank", display_vi: "60–90 giây" },
      { key: "run", label_vi: "Đi bộ dốc/chạy 10 phút", display_vi: "1,3–1,8 km" },
    ],
  },
  female: {
    basic: [
      { key: "push", label_vi: "Chống đẩy", display_vi: "1–6 lần sàn hoặc 6–12 kê bục 20 cm" },
      { key: "pull", label_vi: "Kéo", display_vi: "4–8 kéo người nằm hoặc 2–4 kéo xà trợ lực dây" },
      { key: "squat", label_vi: "Squat thể trọng", display_vi: "18–28 lần" },
      { key: "plank", label_vi: "Plank", display_vi: "30–60 giây" },
      { key: "run", label_vi: "Đi bộ/chạy 10 phút", display_vi: "0,9–1,3 km" },
    ],
    advanced: [
      { key: "push", label_vi: "Chống đẩy", display_vi: "3–8 lần sàn" },
      { key: "pull", label_vi: "Kéo", display_vi: "1–2 kéo xà hoặc 6 kéo người nằm/dây" },
      { key: "squat", label_vi: "Squat thể trọng", display_vi: "20–35 lần" },
      { key: "plank", label_vi: "Plank", display_vi: "45–90 giây" },
      { key: "run", label_vi: "Đi bộ/chạy 10 phút", display_vi: "1,1–1,5 km" },
    ],
  },
};

export default function FitnessTestScreen({
  code,
  offer,
  gender,
  from,
}: {
  code: string;
  offer: ChallengeOfferKey;
  gender: GenderKey;
  from?: string;
}) {
  const router = useRouter();
  const [fromSession, setFromSession] = useState(false);
  const fromBuilder = isFitnessTestFromBuilder(from) || fromSession;
  const adviceHref = `/kiemtratheluc/${encodeURIComponent(code)}/loikhuyen${
    from || fromSession ? `?from=${encodeURIComponent(from || FITNESS_TEST_FROM_BUILDER)}` : ""
  }`;
  const [catalog, setCatalog] = useState<FamiliarizationCatalog | null>(null);
  const [disclaimer, setDisclaimer] = useState(false);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    setFromSession(!!fitnessTestReturnPath());
    aiApi.familiarizationCatalog().then(setCatalog).catch(() => setCatalog(null));
  }, []);

  const level = offerStandardLevel(offer);
  const includeRun = offerIncludesRun(offer);
  const rows = (
    catalog?.standards?.[gender]?.[level] ?? FALLBACK_STANDARDS[gender][level]
  ).filter((row) => includeRun || row.key !== "run");
  const phoneTips = useMemo(
    () => [
      "Đặt điện thoại ngang, tựa tường hoặc giá, cách người 2–3 mét.",
      "Toàn thân (đầu đến chân) phải nằm trong khung. Bật đèn phòng.",
      "Chống đẩy / plank / squat: máy nhìn nghiêng bên hông.",
      "Kéo xà: máy nhìn thẳng hoặc hơi nghiêng, thấy cằm và hai cổ tay.",
      includeRun
        ? "Bài test ~15 phút camera + 10 phút chạy GPS. Có thể hủy và làm lại bất cứ lúc nào."
        : "Bài test ~15 phút camera: khởi động, 4 bài, rồi giãn cơ. Có thể hủy và làm lại bất cứ lúc nào.",
      "Hết giờ từng bài sẽ tự chuyển, hoặc bấm Dừng để sang bài kế.",
    ],
    [includeRun],
  );

  if (started) {
    return (
      <FitnessTestSession
        code={code}
        offer={offer}
        gender={gender}
        onAbort={() => setStarted(false)}
        onFinished={() => router.push(adviceHref)}
      />
    );
  }

  return (
    <div className="space-y-6">
      <header className="rounded-3xl bg-gradient-to-br from-brand-50 via-white to-emerald-50 px-6 py-8 shadow-soft ring-1 ring-brand-100/60 sm:px-8">
        {fromBuilder ? (
          <button
            type="button"
            onClick={() => router.push(builderPathAfterFitnessTest(from))}
            className="mb-3 text-sm font-bold text-brand-700 hover:underline"
          >
            ← Quay lại tạo lịch
          </button>
        ) : null}
        <p className="type-kicker text-brand-600">Kiểm tra thể lực</p>
        <h1 className="mt-2 type-display text-slate-900">
          {offerLabel(offer)}
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          {code && code !== FITNESS_TEST_GUEST_SLUG ? `Mã ${code} · ` : "Mở thử · "}
          {gender === "female" ? "Nữ" : "Nam"} ·{" "}
          {isFoundationExitTest(offer)
            ? "cửa ra nền tảng"
            : `chuẩn ${level === "advanced" ? "nâng cao" : "nền"}`}
        </p>
      </header>

      <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-bold">Tiêu chuẩn gói này</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-700">
          {rows.length
            ? rows.map((row) => (
                <li key={row.key} className="flex justify-between gap-4 border-b border-slate-100 py-2">
                  <span>{row.label_vi}</span>
                  <span className="font-semibold text-slate-900">{row.display_vi}</span>
                </li>
              ))
            : (includeRun
                ? ["Chống đẩy", "Kéo / treo xà", "Squat", "Plank", "Chạy 10 phút"]
                : ["Khởi động", "Chống đẩy", "Kéo / treo xà", "Squat", "Plank", "Giãn cơ"]
              ).map((label) => (
                <li key={label} className="text-slate-500">
                  {label}
                </li>
              ))}
        </ul>
        {gender === "female" && !isFoundationExitTest(offer) && (
          <p className="mt-3 text-sm text-slate-500">
            Nữ: bài kéo là treo xà (tích giây), không bắt buộc kéo cằm qua xà.
          </p>
        )}
      </section>

      <section className="rounded-3xl bg-white p-6 shadow-soft ring-1 ring-slate-100">
        <h2 className="text-lg font-bold">Cách đặt máy và lộ trình</h2>
        <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm leading-relaxed text-slate-700">
          {phoneTips.map((tip) => (
            <li key={tip}>{tip}</li>
          ))}
        </ol>
        <p className="mt-4 rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Giãn cơ 3 phút là bắt buộc. Bỏ qua sẽ đánh failed thể lực — bạn vẫn xem lời khuyên và tạo lịch được.
        </p>
      </section>

      <button
        type="button"
        className="w-full rounded-2xl bg-brand-500 py-4 text-base font-bold text-white shadow-soft hover:bg-brand-600"
        onClick={() => setDisclaimer(true)}
      >
        Bắt đầu test
      </button>
      <p className="text-center text-xs text-slate-500">
        Xác nhận lần này dùng cho điều khoản miễn trách nhiệm. Chi tiết tại{" "}
        <Link href={TERMS_HREF} className="font-semibold text-brand-700">
          điều khoản
        </Link>
        .
      </p>

      <Modal open={disclaimer} onClose={() => setDisclaimer(false)} title="Xác nhận trước khi bật camera">
        <div className="space-y-4 p-5">
          <h2 className="text-lg font-bold">Xác nhận lần cuối</h2>
          <p className="text-sm text-slate-600">
            {includeRun
              ? "Camera và GPS chạy trên máy bạn, không gửi video lên server. Bạn tự chịu trách nhiệm về sức khỏe khi tập."
              : "Camera chạy trên máy bạn, không gửi video lên server. Bạn tự chịu trách nhiệm về sức khỏe khi tập."}
          </p>
          <TermsConsent ageOk={ageOk} termsOk={termsOk} onAgeOk={setAgeOk} onTermsOk={setTermsOk} idPrefix="fit-test" />
          <div className="flex gap-3">
            <button
              type="button"
              disabled={!termsAccepted(ageOk, termsOk)}
              className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white disabled:opacity-40"
              onClick={() => {
                setDisclaimer(false);
                setStarted(true);
              }}
            >
              Bật camera và đếm 15 giây
            </button>
            <button type="button" className="rounded-xl px-4 py-3 text-sm font-bold text-slate-600" onClick={() => setDisclaimer(false)}>
              Đóng
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
