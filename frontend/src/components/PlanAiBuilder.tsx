"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { aiApi, type AiUsage } from "@/lib/authApi";
import { getAccessToken } from "@/lib/auth";
import { addGuestPlanToken } from "@/lib/guestPlans";
import {
  challengeQueryRequested,
  clearAiBuilderDraft,
  loadAiBuilderDraft,
  saveAiBuilderDraft,
  type AiBuilderDraft,
} from "@/lib/aiBuilderDraft";
import {
  ACTIVITY_FIELD_LABEL,
  ACTIVITY_OPTS,
  EXTRA_GOAL_OPTS,
  WEIGHT_GOAL_OPTS,
  formatChallenge100DaysLabel,
  defaultGainKgPerWeek,
  defaultLossKgPerWeek,
  gainWeeklyKgOpts,
  lossWeeklyKgOpts,
} from "@/lib/nutrition";
import type { Activity, ExtraGoal, Food, Gender, Label, WeightGoal } from "@/lib/types";
import {
  collapsePublicEquipmentKeys,
  collapseToWizardEquipmentGroups,
  PUBLIC_EQUIPMENT_LABELS,
  syncWizardEquipmentSelection,
} from "@/lib/equipmentCatalog";
import { REQUIRE_REDEEM_CODE } from "@/lib/config";
import {
  DURATION_OPTS,
  expandWeekDays,
  lookupWeekSplit,
  type ExperienceKey,
} from "@/lib/scheduleSpecMaster";
import { defaultDurationWeeks } from "@/lib/periodization";
import {
  CHALLENGE_WEEKS,
  maxSessionsForLevel,
} from "@/lib/sessionPolicy";
import EquipmentPickerModal from "@/components/EquipmentPickerModal";
import FitnessTestModal from "@/components/FitnessTestModal";
import FoodPickerModal from "@/components/FoodPickerModal";
import Modal from "@/components/Modal";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";
import { countMealRoles, MEAL_POOL_HELP, MEAL_ROLE_OPTS, mealPoolReady } from "@/lib/mealPool";
import { foodDisplayName } from "@/lib/foodDisplay";
import { formatGiftCodeInput, giftCodeFromQuery } from "@/lib/giftCode";
import { redeemCodeApi, type RedeemLookup } from "@/lib/shopApi";

const STEPS_100 = ["Thử thách", "Cá nhân hóa", "Nơi tập", "Trình độ", "Thời gian", "Thực đơn"];
const STEPS_HOME_FOUNDATION = ["Thử thách", "Cá nhân hóa", "Trình độ", "Thời gian"];
const HOME_FOUNDATION_WEEKS = 8;

type ChallengeMode = "challenge_100" | "home_foundation";

const EXPERIENCE_CARDS = [
  {
    value: 1,
    label: "Người mới bắt đầu",
    time: "0–1 tháng",
    who: "Mới vận động, hoặc tập lại sau nghỉ dài.",
    plan: "Lịch nhẹ, học động tác đúng trước khi tăng sức.",
  },
  {
    value: 2,
    label: "Đã có thói quen vận động",
    time: "1–6 tháng",
    who: "Đã quen vài bài cơ bản và tập được đều mỗi tuần.",
    plan: "Lịch vừa sức, tăng dần khối lượng và kỹ thuật.",
  },
  {
    value: 3,
    label: "Tập hoặc chơi thể thao đều",
    time: "6–12 tháng",
    who: "Biết điều chỉnh tạ, nghỉ ngơi và giữ form.",
    plan: "Lịch đầy đủ hơn, có phân nhóm cơ rõ.",
  },
  {
    value: 4,
    label: "Tập luyện, thể dục thường xuyên",
    time: "Trên 12 tháng",
    who: "Nền tảng vững, đã tập ổn định hơn một năm.",
    plan: "Lịch vẫn tạo được. Muốn chuyên sâu thì tìm HLV.",
  },
] as const;

const WEEKDAY_VI: Record<string, string> = {
  "Full Body": "Toàn thân",
  Upper: "Thân trên",
  Lower: "Thân dưới",
  Push: "Đẩy",
  Pull: "Kéo",
  Legs: "Chân",
  "Cardio-Core": "Cardio",
};

function levelToExperienceKey(level: number): ExperienceKey {
  if (level <= 1) return "0-1";
  if (level === 2) return "1-6";
  return "6-24";
}

const PUSHUP_PRESETS = [
  { label: "0", value: "0" },
  { label: "1–5", value: "3" },
  { label: "6–15", value: "10" },
  { label: "16+", value: "20" },
];
const PULLUP_PRESETS = [
  { label: "0", value: "0" },
  { label: "1–3", value: "2" },
  { label: "4–8", value: "6" },
  { label: "9+", value: "12" },
];
const PLANK_PRESETS = [
  { label: "0", value: "0" },
  { label: "<30s", value: "20" },
  { label: "30–60s", value: "45" },
  { label: "60s+", value: "90" },
];
const SQUAT_PRESETS = [
  { label: "0–10", value: "8" },
  { label: "11–25", value: "18" },
  { label: "26+", value: "30" },
];

const MALE_FOCUS_OPTS = [
  { id: "nguc", label: "Ngực Săn" },
  { id: "bung", label: "6 Múi" },
  { id: "lung", label: "Lưng Rộng" },
  { id: "vai", label: "Vai Rộng" },
  { id: "chan", label: "Chân Săn" },
];

const FEMALE_FOCUS_OPTS = [
  { id: "chan", label: "Chân Thon Gọn" },
  { id: "mong", label: "Mông Đầy Đặn" },
  { id: "eo", label: "Giảm Mỡ Bụng" },
  { id: "tay", label: "Tay Thon Gọn" },
];

function focusOptsForGender(g: Gender) {
  return g === "female" ? FEMALE_FOCUS_OPTS : MALE_FOCUS_OPTS;
}

function foldVi(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

function healthNoteConfirmLines(note: string): string[] {
  const t = foldVi(note);
  if (!t.trim()) return [];
  const lines: string[] = [];
  if (/(^|[^a-z])goi([^a-z]|$)/.test(t) || t.includes("khop goi")) {
    lines.push("Gối: lịch sẽ tránh ngồi xổm sâu và bài nhảy.");
  }
  if (/(^|[^a-z])vai([^a-z]|$)/.test(t)) {
    lines.push("Vai: lịch sẽ tránh bài đẩy tạ lên trên đầu.");
  }
  if (/(^|[^a-z])lung([^a-z]|$)/.test(t) || t.includes("cot song")) {
    lines.push("Lưng: lịch sẽ tránh bài kéo tạ nặng từ đất.");
  }
  if (t.includes("co chan") || t.includes("mat ca") || t.includes("ankle")) {
    lines.push("Cổ chân: lịch sẽ tránh bài nhảy.");
  }
  if (t.includes("co tay") || t.includes("wrist")) {
    lines.push("Cổ tay: lịch sẽ hạn chế bài dùng thanh tạ dài.");
  }
  return lines;
}

function extraGoalConfirmLine(goals: ExtraGoal[]): string | null {
  const bits: string[] = [];
  if (goals.includes("physique")) bits.push("ưu tiên bài giúp định hình vóc dáng");
  if (goals.includes("strength")) bits.push("ưu tiên bài dùng nhiều nhóm cơ, số lần ít hơn");
  if (goals.includes("endurance")) bits.push("cuối buổi có phần đi bộ hoặc cardio nhẹ");
  if (goals.includes("mental_health") || goals.includes("heartbreak_recovery")) {
    bits.push("cường độ nhẹ hơn, luôn dừng khi còn sức");
  }
  return bits.length ? `Ưu tiên thêm: ${bits.join("; ")}.` : null;
}

function ConfirmSummaryRow({ label, value }: { label: string; value: string }) {
  return (
    <li className="flex gap-2">
      <span className="w-[7.5rem] shrink-0 font-semibold text-slate-500 sm:w-36">{label}</span>
      <span className="min-w-0 flex-1 text-slate-800">{value}</span>
    </li>
  );
}

function sanitizeIntegerInput(raw: string, maxDigits = 3): string {
  return raw.replace(/[^\d]/g, "").slice(0, maxDigits);
}

/** Allow digits + one decimal point, up to 2 fractional digits. */
function sanitizeWeightInput(raw: string): string {
  const v = raw.replace(/,/g, ".").replace(/[^\d.]/g, "");
  const dot = v.indexOf(".");
  if (dot === -1) return v.slice(0, 3);
  const whole = v.slice(0, dot).slice(0, 3);
  const frac = v
    .slice(dot + 1)
    .replace(/\./g, "")
    .slice(0, 2);
  return frac.length > 0 || v.endsWith(".") ? `${whole}.${frac}` : whole;
}

const MAIN_CHALLENGE_OPTS = WEIGHT_GOAL_OPTS.filter((o) => o.value !== "maintain");

const CHALLENGE_SUB_HINT =
  "Chọn thử thách phụ sẽ ảnh hưởng đến độ khắc nghiệt của thử thách.";

type FoundationMotive = "daily_energy" | "build_habit" | "body_confidence";

const FOUNDATION_MOTIVE_OPTS: { value: FoundationMotive; label: string }[] = [
  { value: "daily_energy", label: "Bớt mệt khi đi lại, làm việc hàng ngày" },
  {
    value: "build_habit",
    label: "Có nền tảng thể lực để tập đều, thử sức cho các mục tiêu cao hơn.",
  },
  { value: "body_confidence", label: "Tự tin hơn với cơ thể từ số 0" },
];

const FOUNDATION_ACTIVITY_OPTS = ACTIVITY_OPTS.filter(
  (o) => o.value === "sedentary" || o.value === "light",
);

const FOUNDATION_EXPERIENCE_OPTS = [
  {
    value: 1,
    label: "Người mới bắt đầu (Chưa từng hoặc cực kỳ ít vận động)",
  },
  {
    value: 2,
    label: "Người đã từng chơi thể thao nhưng bỏ dở một thời gian dài",
  },
] as const;

const GEN_STEPS = [
  { at: 0, label: "Phân tích thể lực & mục tiêu" },
  { at: 6, label: "Chọn bài tập phù hợp" },
  { at: 14, label: "Cân đối dinh dưỡng" },
  { at: 24, label: "Hoàn thiện lịch tuần" },
];

// Overlay "đang tạo lịch" — chỉ thể hiện đang đợi, KHÔNG hiện vị trí / số thứ tự hàng chờ.
function GenerationOverlay({ elapsed }: { elapsed: number }) {
  const activeIdx = GEN_STEPS.reduce((acc, s, i) => (elapsed >= s.at ? i : acc), 0);
  // Ước lượng ~30s; không bao giờ chạm 100% khi chưa xong (overlay unmount khi xong).
  const progress = Math.min(95, Math.round((elapsed / 30) * 100));
  const reassurance =
    elapsed > 70
      ? "Vẫn đang tạo, cảm ơn bạn đã đợi."
      : elapsed > 35
        ? "Đang hoàn thiện, sắp xong…"
        : "";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4 backdrop-blur-sm"
      role="alertdialog"
      aria-busy="true"
      aria-label="Đang tạo lịch tập"
    >
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center gap-3">
          <span className="inline-block h-8 w-8 animate-spin rounded-full border-[3px] border-brand-200 border-t-brand-500" />
          <div>
            <p className="text-base font-bold text-slate-800">TAPTOT đang tạo lịch của bạn…</p>
            <p className="text-xs text-slate-500">Vui lòng giữ màn hình, thường mất khoảng 20–40 giây.</p>
          </div>
        </div>

        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className="h-full rounded-full bg-brand-500 transition-all duration-1000 ease-out"
            style={{ width: `${Math.max(6, progress)}%` }}
          />
        </div>

        <ul className="mt-4 space-y-2">
          {GEN_STEPS.map((s, i) => {
            const done = i < activeIdx;
            const active = i === activeIdx;
            return (
              <li key={s.label} className="flex items-center gap-2.5 text-sm">
                <span
                  className={`grid h-5 w-5 shrink-0 place-items-center rounded-full text-[11px] font-bold ${
                    done
                      ? "bg-brand-500 text-white"
                      : active
                        ? "bg-brand-100 text-brand-700 ring-2 ring-brand-200"
                        : "bg-slate-100 text-slate-400"
                  }`}
                >
                  {done ? "✓" : active ? "…" : i + 1}
                </span>
                <span className={done || active ? "font-medium text-slate-700" : "text-slate-400"}>
                  {s.label}
                </span>
              </li>
            );
          })}
        </ul>

        {reassurance && <p className="mt-4 text-center text-xs font-medium text-slate-500">{reassurance}</p>}
      </div>
    </div>
  );
}

function Stepper({
  step,
  onGo,
  steps,
}: {
  step: number;
  onGo: (n: number) => void;
  steps: string[];
}) {
  // Chỉ ẩn các bước sau khi còn ở bước Thử thách; sau Tiếp tục hiện đủ toàn bộ.
  const visible = step === 1 ? steps.slice(0, 1) : steps;
  return (
    <div className="mb-6">
      <div className="flex items-center gap-1.5 sm:gap-2" aria-label={`Bước ${step} / ${steps.length}`}>
        {visible.map((label, i) => {
          const n = i + 1;
          const active = n === step;
          const done = n < step;
          return (
            <div
              key={label}
              className="flex min-w-0 flex-1 items-center gap-1.5 sm:gap-2 animate-in"
            >
              <button
                type="button"
                disabled={!done}
                onClick={() => onGo(n)}
                className="flex min-w-0 items-center gap-2 disabled:cursor-default"
                aria-current={active ? "step" : undefined}
              >
                <div
                  className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold transition ${
                    done
                      ? "bg-brand-500 text-white"
                      : active
                        ? "bg-brand-500 text-white ring-4 ring-brand-100"
                        : "bg-slate-200 text-slate-400"
                  }`}
                >
                  {done ? "✓" : n}
                </div>
                <span
                  className={`hidden truncate text-sm font-semibold leading-tight sm:inline ${
                    active || done ? "text-slate-700" : "text-slate-400"
                  }`}
                >
                  {label}
                </span>
              </button>
              {n < visible.length && (
                <div
                  className={`h-0.5 min-w-[0.5rem] flex-1 rounded transition-colors duration-300 ${
                    done ? "bg-brand-500" : "bg-slate-200"
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function PlanAiBuilder() {
  const router = useRouter();
  const pathname = usePathname();
  const skipDurationSyncRef = useRef(false);
  const [step, setStep] = useState(1);
  const [goal, setGoal] = useState<WeightGoal>("lose_weight");
  const [extraGoals, setExtraGoals] = useState<ExtraGoal[]>([]);
  const [gender, setGender] = useState<Gender>("male");
  const [age, setAge] = useState("25");
  const [height, setHeight] = useState("170");
  const [weight, setWeight] = useState("65");
  const [activity, setActivity] = useState<Activity>("moderate");
  const [experienceLevel, setExperienceLevel] = useState(1);
  const [durationWeeks, setDurationWeeks] = useState(CHALLENGE_WEEKS);
  const [challengeMode, setChallengeMode] = useState<ChallengeMode>("challenge_100");
  const challenge100Days = challengeMode === "challenge_100";
  const homeFoundation = challengeMode === "home_foundation";
  const wizardSteps = homeFoundation ? STEPS_HOME_FOUNDATION : STEPS_100;
  const [foundationMotive, setFoundationMotive] = useState<FoundationMotive>("build_habit");
  const [giftCode, setGiftCode] = useState("");
  const [giftLookup, setGiftLookup] = useState<RedeemLookup | null>(null);
  const [giftChecking, setGiftChecking] = useState(false);
  const [gateCodeError, setGateCodeError] = useState("");
  const [accessGateOpen, setAccessGateOpen] = useState(false);
  const [kgPerWeek, setKgPerWeek] = useState(() => defaultLossKgPerWeek(65));
  const [sessionsPerWeek, setSessionsPerWeek] = useState(3);
  const [sessionMinutes, setSessionMinutes] = useState(60);
  const [location, setLocation] = useState<"home" | "gym">("home");
  const [focus, setFocus] = useState<string[]>([]);
  const [equipment, setEquipment] = useState<string[]>([]);
  const [equipLabels, setEquipLabels] = useState<Record<string, string>>({});
  const [equipModalOpen, setEquipModalOpen] = useState(false);
  /** Chỉ dùng khi location === "home": true = không dụng cụ, false = chọn từ kho */
  const [noEquipment, setNoEquipment] = useState(true);
  const [selectedFoods, setSelectedFoods] = useState<Record<number, Food>>({});
  const [foodModalOpen, setFoodModalOpen] = useState(false);
  const [fitnessOpen, setFitnessOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);
  const [aiSuggestFoods, setAiSuggestFoods] = useState(true);
  const [pushups, setPushups] = useState("");
  const [pullups, setPullups] = useState("");
  const [plankSeconds, setPlankSeconds] = useState("");
  const [squats, setSquats] = useState("");
  const [healthNote, setHealthNote] = useState("");
  const [loading, setLoading] = useState(false);
  const [genElapsed, setGenElapsed] = useState(0);
  const [err, setErr] = useState("");
  const [aiUsage, setAiUsage] = useState<AiUsage | null>(null);

  const weightKg = Number.parseFloat(weight);
  const lossOpts = useMemo(
    () => lossWeeklyKgOpts(Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65),
    [weightKg],
  );
  const gainOpts = useMemo(
    () => gainWeeklyKgOpts(Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65),
    [weightKg],
  );

  useEffect(() => {
    if (!loading) {
      setGenElapsed(0);
      return;
    }
    const timer = setInterval(() => setGenElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    aiApi
      .usage()
      .then(setAiUsage)
      .catch(() => setAiUsage(null));
  }, []);

  const maxSessions = maxSessionsForLevel(experienceLevel);

  useEffect(() => {
    setSessionsPerWeek((n) => Math.min(n, maxSessionsForLevel(experienceLevel)));
  }, [experienceLevel]);

  useEffect(() => {
    if (skipDurationSyncRef.current) {
      skipDurationSyncRef.current = false;
      return;
    }
    if (challenge100Days) return;
    if (homeFoundation) {
      setDurationWeeks(HOME_FOUNDATION_WEEKS);
      return;
    }
    setDurationWeeks(defaultDurationWeeks(experienceLevel));
  }, [experienceLevel, challenge100Days, homeFoundation]);

  useEffect(() => {
    const w = Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65;
    if (goal === "lose_weight") {
      const allowed = lossOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) {
        setKgPerWeek(defaultLossKgPerWeek(w));
      }
      return;
    }
    if (goal === "gain_weight") {
      const allowed = gainOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) {
        setKgPerWeek(defaultGainKgPerWeek(w));
      }
    }
  }, [goal, gainOpts, kgPerWeek, lossOpts, weightKg]);

  useEffect(() => {
    const draft = loadAiBuilderDraft();
    const wantChallenge = challengeQueryRequested();
    const code = giftCodeFromQuery();
    if (code) setGiftCode(code);
    if (code) {
      redeemCodeApi
        .lookup(code)
        .then((d) => {
          if (d.valid) setGiftLookup(d);
        })
        .catch(() => {});
    }
    if (draft) {
      skipDurationSyncRef.current = true;
      applyDraft(draft);
      clearAiBuilderDraft();
    } else if (wantChallenge) {
      setChallengeMode("challenge_100");
      setDurationWeeks(CHALLENGE_WEEKS);
    }
    if (wantChallenge) {
      const taptotPath = pathname.startsWith("/tai-khoan")
        ? "/tai-khoan/tao-lich-tap/taptot"
        : "/tao-lich-tap/taptot";
      const qs = code ? `?code=${encodeURIComponent(code)}` : "";
      router.replace(`${taptotPath}${qs}`);
    }
  }, [pathname, router]);

  async function submitGiftCode() {
    const formatted = formatGiftCodeInput(giftCode);
    if (formatted.replace(/-/g, "").length < 10) {
      setGiftLookup(null);
      setGateCodeError("Nhập đủ mã trên tem, dạng TT-XXXX-XXXX.");
      return;
    }
    setGiftChecking(true);
    setGateCodeError("");
    try {
      const result = await redeemCodeApi.lookup(formatted);
      setGiftLookup(result);
      if (!result.valid) {
        setGateCodeError("Mã đã được sử dụng hoặc không đúng.");
        return;
      }
      setAccessGateOpen(false);
      setStep(2);
    } catch {
      setGiftLookup({ valid: false, status: "invalid" });
      setGateCodeError("Không kiểm tra được mã. Thử lại sau.");
    } finally {
      setGiftChecking(false);
    }
  }

  function applyDraft(draft: AiBuilderDraft) {
    setStep(Math.min(Math.max(Math.round(draft.step), 1), STEPS_100.length));
    setGoal(draft.goal === "maintain" ? "lose_weight" : draft.goal);
    setExtraGoals(draft.extraGoals);
    setGender(draft.gender);
    setAge(draft.age);
    setHeight(draft.height);
    setWeight(draft.weight);
    setActivity(draft.activity);
    setExperienceLevel(draft.experienceLevel);
    setChallengeMode("challenge_100");
    setDurationWeeks(CHALLENGE_WEEKS);
    setKgPerWeek(draft.kgPerWeek);
    setSessionsPerWeek(draft.sessionsPerWeek);
    setSessionMinutes(draft.sessionMinutes);
    setLocation(draft.location);
    setFocus(draft.focus.filter((id) => focusOptsForGender(draft.gender).some((o) => o.id === id)));
    setEquipment(syncWizardEquipmentSelection(collapsePublicEquipmentKeys(draft.equipment)));
    setEquipLabels(() => {
      const keys = syncWizardEquipmentSelection(collapsePublicEquipmentKeys(draft.equipment));
      const next: Record<string, string> = {};
      for (const key of keys) {
        next[key] =
          draft.equipLabels[key] ||
          (key === "resistance-band"
            ? draft.equipLabels["resistance-band-1"] ||
              draft.equipLabels["resistance-band-2"] ||
              PUBLIC_EQUIPMENT_LABELS["resistance-band"]
            : PUBLIC_EQUIPMENT_LABELS[key as keyof typeof PUBLIC_EQUIPMENT_LABELS]) ||
          key;
      }
      return next;
    });
    setNoEquipment(draft.noEquipment);
    setSelectedFoods(draft.selectedFoods);
    setAiSuggestFoods(draft.aiSuggestFoods);
    setPushups(draft.pushups);
    setPullups(draft.pullups);
    setPlankSeconds(draft.plankSeconds);
    setSquats(draft.squats);
    setHealthNote(draft.healthNote);
  }

  function captureDraft(): AiBuilderDraft {
    return {
      step,
      goal,
      extraGoals,
      gender,
      age,
      height,
      weight,
      activity,
      experienceLevel,
      durationWeeks,
      challenge100Days: true,
      kgPerWeek,
      sessionsPerWeek,
      sessionMinutes,
      location,
      focus,
      equipment: syncWizardEquipmentSelection(collapsePublicEquipmentKeys(equipment)),
      equipLabels,
      noEquipment,
      selectedFoods,
      aiSuggestFoods,
      pushups,
      pullups,
      plankSeconds,
      squats,
      healthNote,
    };
  }

  function toggleFocus(id: string) {
    setFocus((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleExtraGoal(id: ExtraGoal) {
    setExtraGoals((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function removeEquipGroup(groupId: string) {
    const group = collapseToWizardEquipmentGroups(equipment).find((g) => g.id === groupId);
    if (!group) return;
    const drop = new Set<string>(group.slugs);
    setEquipment((prev) => prev.filter((x) => !drop.has(x)));
  }

  function saveEquipment(keys: string[], items: Label[]) {
    const nextKeys = syncWizardEquipmentSelection(collapsePublicEquipmentKeys(keys));
    setEquipment(nextKeys);
    if (nextKeys.length > 0) setNoEquipment(false);
    setEquipLabels((prev) => {
      const next = { ...prev };
      for (const item of items) next[item.key] = item.label_vi;
      for (const key of nextKeys) {
        if (!next[key]) {
          next[key] =
            PUBLIC_EQUIPMENT_LABELS[key as keyof typeof PUBLIC_EQUIPMENT_LABELS] || key;
        }
      }
      return next;
    });
    setErr("");
  }

  function selectLocation(next: "home" | "gym") {
    setLocation(next);
    setEquipModalOpen(false);
    setErr("");
    if (next === "gym") {
      setEquipment([]);
      setNoEquipment(false);
      setFitnessOpen(false);
      return;
    }
    // Nhà: mặc định «Không dụng cụ», xóa lựa chọn kho
    setEquipment([]);
    setNoEquipment(true);
  }

  function selectHomeEquipmentMode(mode: "none" | "with") {
    setErr("");
    if (mode === "none") {
      setNoEquipment(true);
      setEquipment([]);
      setEquipModalOpen(false);
      return;
    }
    setNoEquipment(false);
  }

  function removeFood(id: number) {
    setSelectedFoods((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
  }

  function saveFoods(next: Record<number, Food>) {
    setSelectedFoods(next);
    setErr("");
  }

  const experienceComingSoon = experienceLevel >= 4;

  function validatePersonalization(): string | null {
    const ageRaw = age.trim();
    if (!ageRaw) return "Vui lòng nhập tuổi.";
    if (!/^\d+$/.test(ageRaw)) return "Tuổi chỉ gồm số nguyên, không thập phân hay ký tự lạ.";
    const a = Number(ageRaw);
    if (a < 16 || a > 150) return "Tuổi phải từ 16 đến 150.";

    const heightRaw = height.trim();
    if (!heightRaw) return "Vui lòng nhập chiều cao.";
    if (!/^\d+$/.test(heightRaw)) {
      return "Chiều cao chỉ gồm số nguyên (cm), không thập phân hay ký tự lạ.";
    }
    const h = Number(heightRaw);
    if (h < 50 || h > 250) return "Chiều cao phải từ 50 đến 250 cm.";

    const weightRaw = weight.trim().replace(/,/g, ".");
    if (!weightRaw) return "Vui lòng nhập cân nặng.";
    if (!/^\d+(\.\d{1,2})?$/.test(weightRaw)) {
      return "Cân nặng không hợp lệ (cho phép tối đa 2 chữ số thập phân).";
    }
    const w = Number(weightRaw);
    if (!(w >= 20 && w <= 400)) return "Cân nặng phải từ 20 đến 400 kg.";

    if (gender !== "male" && gender !== "female") return "Vui lòng chọn giới tính.";
    const activityOpts = homeFoundation ? FOUNDATION_ACTIVITY_OPTS : ACTIVITY_OPTS;
    if (!activityOpts.some((o) => o.value === activity)) {
      return "Vui lòng chọn mức hoạt động hàng ngày.";
    }
    if (homeFoundation) {
      if (!FOUNDATION_MOTIVE_OPTS.some((o) => o.value === foundationMotive)) {
        return "Vui lòng chọn mục tiêu chính.";
      }
      return null;
    }
    if (!MAIN_CHALLENGE_OPTS.some((o) => o.value === goal)) {
      return "Vui lòng chọn thử thách chính.";
    }
    const subOpts = goal === "gain_weight" ? gainOpts : lossOpts;
    if (!subOpts.some((o) => o.value === kgPerWeek)) {
      return "Vui lòng chọn thử thách phụ.";
    }
    return null;
  }

  function selectChallengeMode(mode: ChallengeMode) {
    setChallengeMode(mode);
    setExtraGoals([]);
    if (mode === "challenge_100") {
      setDurationWeeks(CHALLENGE_WEEKS);
      if (goal === "maintain") setGoal("lose_weight");
      return;
    }
    setDurationWeeks(HOME_FOUNDATION_WEEKS);
    setLocation("home");
    setNoEquipment(true);
    setEquipment([]);
    setAiSuggestFoods(true);
    setSelectedFoods({});
    setFocus([]);
    setExperienceLevel(1);
    setGoal("maintain");
    setFoundationMotive("build_habit");
    if (activity !== "sedentary" && activity !== "light") {
      setActivity("sedentary");
    }
  }

  const testsFilled = [pushups, pullups, plankSeconds, squats].filter((v) => v !== "").length;

  function goNext() {
    setErr("");
    if (step === 1) {
      if (homeFoundation || !REQUIRE_REDEEM_CODE || giftLookup?.valid) {
        setStep(2);
      } else {
        setGateCodeError("");
        setAccessGateOpen(true);
      }
      return;
    }
    if (step === 2) {
      const msg = validatePersonalization();
      if (msg) {
        setErr(msg);
        return;
      }
      setStep(3);
      return;
    }
    if (homeFoundation) {
      if (step === 3) {
        if (testsFilled < 4) {
          setErr("Cần đủ 4 ô ước lượng sức (có thể là 0) trước khi tiếp tục.");
          setFitnessOpen(true);
          return;
        }
        setStep(4);
        return;
      }
      return;
    }
    if (step === 3) {
      if (location === "home" && !noEquipment && equipment.length === 0) {
        setErr("Hãy chọn ít nhất 1 dụng cụ từ kho, hoặc chọn «Không dụng cụ».");
        return;
      }
      setStep(4);
      return;
    }
    if (step === 4) {
      setStep(5);
      return;
    }
    if (step === 5) {
      setStep(6);
    }
  }

  function requestConfirm() {
    setErr("");
    if (!homeFoundation && REQUIRE_REDEEM_CODE && !giftLookup?.valid) {
      setConfirmOpen(false);
      setAccessGateOpen(true);
      return;
    }
    const msg = validatePersonalization();
    if (msg) {
      setErr(msg);
      setStep(2);
      return;
    }
    if (homeFoundation) {
      if (testsFilled < 4) {
        setErr("Cần đủ 4 ô ước lượng sức (có thể là 0) trước khi tạo lịch.");
        setStep(3);
        setFitnessOpen(true);
        return;
      }
    } else if (location === "home" && !noEquipment && equipment.length === 0) {
      setErr("Hãy chọn ít nhất 1 dụng cụ từ kho, hoặc chọn «Không dụng cụ».");
      setStep(3);
      return;
    }
    if (!homeFoundation && !aiSuggestFoods && !mealPoolReady(Object.values(selectedFoods))) {
      setErr(MEAL_POOL_HELP);
      setStep(6);
      return;
    }
    setAgeOk(false);
    setTermsOk(false);
    setConfirmOpen(true);
  }

  async function generate() {
    if (!termsAccepted(ageOk, termsOk)) return;
    setErr("");
    if (!homeFoundation && REQUIRE_REDEEM_CODE && !giftLookup?.valid) {
      setConfirmOpen(false);
      setAccessGateOpen(true);
      return;
    }
    const msg = validatePersonalization();
    if (msg) {
      setErr(msg);
      setStep(2);
      return;
    }
    if (homeFoundation) {
      if (testsFilled < 4) {
        setErr("Cần đủ 4 ô ước lượng sức (có thể là 0) trước khi tạo lịch.");
        setStep(3);
        setFitnessOpen(true);
        return;
      }
    } else if (location === "home" && !noEquipment && equipment.length === 0) {
      setErr("Hãy chọn ít nhất 1 dụng cụ từ kho, hoặc chọn «Không dụng cụ».");
      setStep(3);
      return;
    }
    if (!homeFoundation && !aiSuggestFoods && !mealPoolReady(Object.values(selectedFoods))) {
      setErr(MEAL_POOL_HELP);
      setStep(6);
      return;
    }
    setConfirmOpen(false);
    setLoading(true);
    try {
      const atHome = homeFoundation || location === "home";
      const homeNoEquip = homeFoundation || (atHome && noEquipment);
      const res = await aiApi.generateWorkout({
        goal: homeFoundation ? "maintain" : goal,
        gender,
        age: parseInt(age, 10),
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        activity,
        sessions_per_week: sessionsPerWeek,
        session_minutes: sessionMinutes,
        location: homeFoundation ? "home" : location,
        focus_areas: homeFoundation ? [] : focus,
        extra_goals: challenge100Days || homeFoundation ? [] : extraGoals,
        equipment_list:
          atHome && !homeNoEquip
            ? syncWizardEquipmentSelection(collapsePublicEquipmentKeys(equipment))
            : [],
        food_ids: homeFoundation || aiSuggestFoods ? [] : Object.keys(selectedFoods).map(Number),
        experience_level: homeFoundation ? Math.min(Math.max(experienceLevel, 1), 2) : experienceLevel,
        ai_suggest_equipment: false,
        no_equipment: homeNoEquip,
        ai_suggest_foods: homeFoundation ? false : aiSuggestFoods,
        fitness_baseline: atHome
          ? {
              pushups_max: pushups !== "" ? Number(pushups) : null,
              pullups_max: pullups !== "" ? Number(pullups) : null,
              plank_seconds: plankSeconds !== "" ? Number(plankSeconds) : null,
              squats_max: squats !== "" ? Number(squats) : null,
            }
          : {
              pushups_max: null,
              pullups_max: null,
              plank_seconds: null,
              squats_max: null,
            },
        health_note: healthNote.trim() || null,
        duration_weeks: homeFoundation ? HOME_FOUNDATION_WEEKS : durationWeeks,
        kg_per_week:
          homeFoundation || (goal !== "lose_weight" && goal !== "gain_weight")
            ? undefined
            : kgPerWeek,
        challenge_100_days: challenge100Days || undefined,
        generation_mode: homeFoundation ? "free_home" : undefined,
        foundation_motive: homeFoundation ? foundationMotive : undefined,
        redeem_code: homeFoundation ? undefined : giftCode || undefined,
      });
      if (res.usage) setAiUsage(res.usage);
      const token = res.share_token;
      if (token) {
        if (!getAccessToken()) addGuestPlanToken(token);
        const tem = res.code_applied ? "&tem=1" : "";
        router.push(`/lich/${token}?moi=1${tem}`);
        return;
      }
      setErr("Đã tạo lịch nhưng chưa có link xem. Thử lại hoặc mở lại từ thiết bị này sau.");
    } catch (ex) {
      setErr((ex as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const selectedFoodList = Object.values(selectedFoods);
  const goalLabel = WEIGHT_GOAL_OPTS.find((o) => o.value === goal)?.label ?? goal;
  const extraLabels = EXTRA_GOAL_OPTS.filter((o) => extraGoals.includes(o.value)).map((o) => o.label);
  const extraGoalLine = extraGoalConfirmLine(extraGoals);
  const healthLines = healthNoteConfirmLines(healthNote);
  const fitnessSummary =
    homeFoundation || location === "home"
      ? ([
          pushups !== "" ? `Chống đẩy ${pushups} cái` : null,
          pullups !== "" ? `Pull-up ${pullups} cái` : null,
          plankSeconds !== "" ? `Plank ${plankSeconds} giây` : null,
          squats !== "" ? `Squat ${squats} cái` : null,
        ].filter(Boolean) as string[])
      : [];
  const l3WithoutTests =
    !homeFoundation && location === "home" && experienceLevel >= 3 && testsFilled < 2;
  const sedentaryHighFreq = activity === "sedentary" && sessionsPerWeek >= 5;
  const focusLabels = focusOptsForGender(gender)
    .filter((o) => focus.includes(o.id))
    .map((o) => o.label);
  const clampedSessions = Math.min(sessionsPerWeek, maxSessions);
  const beginnerHighFreq = experienceLevel <= 1 && clampedSessions >= 5;
  const selectedWizardGroups = useMemo(
    () => collapseToWizardEquipmentGroups(equipment),
    [equipment],
  );
  const equipSummary = homeFoundation
    ? "Nhà · không dụng cụ"
    : location === "gym"
      ? "Phòng gym"
      : noEquipment
        ? "Nhà · không dụng cụ"
        : selectedWizardGroups.length
          ? `Nhà · ${selectedWizardGroups.map((g) => g.label_vi).join(", ")}`
          : "Nhà · chưa chọn dụng cụ";
  const foodSummary = homeFoundation
    ? "Không kèm thực đơn"
    : aiSuggestFoods
      ? "TAPTOT gợi ý thực đơn"
      : selectedFoodList.length
        ? `Bạn đã chọn ${selectedFoodList.length} món`
        : "Chưa chọn món";
  const challengeSummary = challenge100Days
    ? "100 ngày thay đổi vóc dáng (14 tuần)"
    : homeFoundation
      ? "Cải thiện thể lực tại nhà từ con số 0 (8 tuần)"
      : "Lịch 1 tháng (4 tuần)";
  const splitCode = lookupWeekSplit({
    experience: levelToExperienceKey(experienceLevel),
    sessions: clampedSessions,
    gender,
    location: homeFoundation ? "home" : location,
    homeEquip: homeFoundation || noEquipment ? "no_equip" : "with_equip",
  });
  const previewWeekCode =
    beginnerHighFreq ? "Upper, Lower, Upper, Lower, Full Body" : splitCode;
  const splitDays = previewWeekCode
    ? expandWeekDays(previewWeekCode).map((d) => WEEKDAY_VI[d] || d)
    : [];
  const goalSummary = homeFoundation
    ? FOUNDATION_MOTIVE_OPTS.find((o) => o.value === foundationMotive)?.label ?? foundationMotive
    : goal === "lose_weight" || goal === "gain_weight"
      ? `${goalLabel} · ${formatChallenge100DaysLabel(goal, kgPerWeek)}`
      : goalLabel;
  const scheduleSummary = `${Math.min(sessionsPerWeek, maxSessions)} buổi/tuần · ${sessionMinutes} phút mỗi buổi`;
  const giftSummary = giftCode
    ? giftLookup?.valid
      ? `${giftCode} · mã hợp lệ, dùng 1 lần khi tạo lịch`
      : `${giftCode} · mã không còn hiệu lực`
    : "";
  const roleCounts = countMealRoles(selectedFoodList);

  return (
    <section className="space-y-6">
      {loading && <GenerationOverlay elapsed={genElapsed} />}
      <div>
        <h1 className="text-2xl font-extrabold tracking-tight">Bắt đầu với TAPTOT</h1>
        {aiUsage && !aiUsage.openai_configured ? (
          <p className="mt-2 text-xs font-medium text-slate-500">Đang dùng lịch mẫu hệ thống.</p>
        ) : null}
        {giftLookup?.valid ? (
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 rounded-xl bg-brand-50 px-3 py-2.5">
            <p className="text-sm text-brand-900">
              Mã kèm sản phẩm {giftCode} · dùng 1 lần khi lịch được tạo
            </p>
            <button
              type="button"
              onClick={() => {
                setGateCodeError("");
                setAccessGateOpen(true);
              }}
              className="text-xs font-semibold text-brand-700 hover:underline"
            >
              Đổi mã
            </button>
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl bg-white p-5 shadow-soft">
        <Stepper
          step={step}
          steps={wizardSteps}
          onGo={(n) => {
            setErr("");
            if (n > 1 && !homeFoundation && REQUIRE_REDEEM_CODE && !giftLookup?.valid) {
              setAccessGateOpen(true);
              return;
            }
            if (n > 2) {
              const msg = validatePersonalization();
              if (msg) {
                setErr(msg);
                setStep(2);
                return;
              }
            }
            setStep(n);
          }}
        />

        {step === 1 && (
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">Chọn thử thách</p>
              <div className="grid grid-cols-1 gap-3">
                <button
                  type="button"
                  onClick={() => selectChallengeMode("challenge_100")}
                  className={`rounded-2xl border-2 px-4 py-4 text-left ${
                    challenge100Days
                      ? "border-amber-500 bg-amber-50 ring-2 ring-amber-400/30"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <span className="text-lg font-extrabold text-slate-900">100 ngày thay đổi vóc dáng</span>
                </button>
                <button
                  type="button"
                  onClick={() => selectChallengeMode("home_foundation")}
                  className={`rounded-2xl border-2 px-4 py-4 text-left ${
                    homeFoundation
                      ? "border-amber-500 bg-amber-50 ring-2 ring-amber-400/30"
                      : "border-slate-200 bg-white"
                  }`}
                >
                  <span className="text-lg font-extrabold text-slate-900">
                    Cải thiện thể lực tại nhà từ con số 0
                  </span>
                </button>
              </div>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-5">
            <div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-sm font-semibold text-slate-600" htmlFor="ai-age">Tuổi</label>
                  <input
                    id="ai-age"
                    className="field mt-1"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="16–150"
                    value={age}
                    onChange={(e) => setAge(sanitizeIntegerInput(e.target.value, 3))}
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-600" htmlFor="ai-height">Cao (cm)</label>
                  <input
                    id="ai-height"
                    className="field mt-1"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    placeholder="50–250"
                    value={height}
                    onChange={(e) => setHeight(sanitizeIntegerInput(e.target.value, 3))}
                  />
                </div>
                <div>
                  <label className="text-sm font-semibold text-slate-600" htmlFor="ai-weight">Nặng (kg)</label>
                  <input
                    id="ai-weight"
                    className="field mt-1"
                    type="text"
                    inputMode="decimal"
                    autoComplete="off"
                    placeholder="vd. 65.5"
                    value={weight}
                    onChange={(e) => setWeight(sanitizeWeightInput(e.target.value))}
                  />
                </div>
              </div>
              <div className="mt-3">
                <label className="mb-1.5 block text-sm font-semibold text-slate-600">Giới tính</label>
                <div className="grid grid-cols-2 gap-2">
                  {(["male", "female"] as Gender[]).map((g) => (
                    <button
                      key={g}
                      type="button"
                      onClick={() => {
                        setGender(g);
                        const allowed = new Set(focusOptsForGender(g).map((o) => o.id));
                        setFocus((prev) => prev.filter((id) => allowed.has(id)));
                      }}
                      className={`rounded-xl border py-2.5 font-semibold ${
                        gender === g ? "border-brand-500 bg-brand-500 text-white" : "border-slate-200"
                      }`}
                    >
                      {g === "male" ? "Nam" : "Nữ"}
                    </button>
                  ))}
                </div>
              </div>
              <div className="mt-3">
                <label className="mb-1.5 block text-sm font-semibold text-slate-600" htmlFor="ai-activity">
                  {ACTIVITY_FIELD_LABEL}
                </label>
                <select
                  id="ai-activity"
                  className="field"
                  value={activity}
                  onChange={(e) => setActivity(e.target.value as Activity)}
                >
                  {(homeFoundation ? FOUNDATION_ACTIVITY_OPTS : ACTIVITY_OPTS).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {homeFoundation ? (
              <div>
                <label className="mb-1.5 block text-sm font-semibold text-slate-600">Mục tiêu chính</label>
                <div className="grid grid-cols-1 gap-2">
                  {FOUNDATION_MOTIVE_OPTS.map((o) => (
                    <button
                      key={o.value}
                      type="button"
                      onClick={() => setFoundationMotive(o.value)}
                      className={`rounded-xl border px-3 py-3 text-left text-sm font-semibold leading-snug ${
                        foundationMotive === o.value
                          ? "border-brand-500 bg-brand-50 text-brand-700"
                          : "border-slate-200 text-slate-600"
                      }`}
                    >
                      {o.label}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <>
                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-slate-600">Thử thách chính</label>
                  <div className="grid grid-cols-2 gap-2">
                    {MAIN_CHALLENGE_OPTS.map((o) => (
                      <button
                        key={o.value}
                        type="button"
                        onClick={() => {
                          setGoal(o.value);
                          const w = Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65;
                          if (o.value === "lose_weight") setKgPerWeek(defaultLossKgPerWeek(w));
                          else if (o.value === "gain_weight") setKgPerWeek(defaultGainKgPerWeek(w));
                        }}
                        className={`rounded-xl border py-2.5 text-sm font-semibold ${
                          goal === o.value ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200 text-slate-500"
                        }`}
                      >
                        {o.icon} {o.label}
                      </button>
                    ))}
                  </div>
                </div>

                {!challenge100Days && (
                  <div>
                    <label className="mb-1.5 block text-sm font-semibold text-slate-600">
                      Ưu tiên thêm <span className="font-normal text-slate-400">(chọn nhiều)</span>
                    </label>
                    <div className="flex flex-wrap gap-2">
                      {EXTRA_GOAL_OPTS.map((o) => (
                        <button
                          key={o.value}
                          type="button"
                          onClick={() => toggleExtraGoal(o.value)}
                          className={`chip ${extraGoals.includes(o.value) ? "chip-active" : ""}`}
                        >
                          {o.icon} {o.label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                <div>
                  <label className="mb-1.5 block text-sm font-semibold text-slate-600">Thử thách phụ</label>
                  <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                    {(goal === "gain_weight" ? gainOpts : lossOpts).map((o) => {
                      const subKind = goal === "gain_weight" ? "gain_weight" : "lose_weight";
                      return (
                        <button
                          key={`${o.hint}-${o.value}`}
                          type="button"
                          onClick={() => setKgPerWeek(o.value)}
                          className={`rounded-xl border px-3 py-3 text-center transition ${
                            kgPerWeek === o.value
                              ? "border-brand-500 bg-brand-50 text-brand-800"
                              : "border-slate-200 text-slate-600"
                          }`}
                        >
                          <span className="block text-sm font-extrabold leading-snug tracking-tight sm:text-[15px]">
                            {formatChallenge100DaysLabel(subKind, o.value)}
                          </span>
                          {"recommended" in o && o.recommended ? (
                            <span className="mt-1.5 inline-block rounded-full bg-brand-100 px-1.5 py-px text-[10px] font-bold text-brand-700">
                              Gợi ý
                            </span>
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                  <p className="mt-1.5 text-xs text-slate-400">{CHALLENGE_SUB_HINT}</p>
                </div>
              </>
            )}
          </div>
        )}

        {(homeFoundation ? step === 3 : step === 4) && (
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-600" htmlFor="ai-experience">
                Kinh nghiệm tập luyện
              </label>
              <select
                id="ai-experience"
                className="field"
                value={
                  homeFoundation
                    ? experienceLevel <= 1
                      ? 1
                      : 2
                    : experienceLevel
                }
                onChange={(e) => setExperienceLevel(Number(e.target.value))}
              >
                {(homeFoundation ? FOUNDATION_EXPERIENCE_OPTS : EXPERIENCE_CARDS).map((lv) => (
                  <option key={lv.value} value={lv.value}>
                    {"time" in lv ? `${lv.label} (${lv.time})` : lv.label}
                  </option>
                ))}
              </select>
              {!homeFoundation && experienceComingSoon && (
                <p className="mt-2 text-xs text-slate-500">
                  Lịch vẫn tạo được. Nếu muốn chương trình riêng,{" "}
                  <Link href="/lien-he" className="font-semibold text-brand-600 hover:underline">
                    tìm huấn luyện viên
                  </Link>
                  .
                </p>
              )}
            </div>

            {(homeFoundation || location === "home") && (
              <div>
                <p className="mb-3 text-sm font-semibold text-slate-600">
                  {homeFoundation ? "Ước lượng sức hiện tại" : "Thể lực cơ bản"}
                </p>
                <button
                  type="button"
                  onClick={() => setFitnessOpen(true)}
                  className="w-full rounded-xl border border-dashed border-brand-300 bg-brand-50/50 px-4 py-3 text-sm font-bold text-brand-700 hover:bg-brand-50"
                >
                  {homeFoundation
                    ? fitnessSummary.length
                      ? "Chỉnh lại ước lượng"
                      : "Ước lượng sức hiện tại"
                    : fitnessSummary.length
                      ? "Chỉnh lại thể lực"
                      : "Kiểm tra thể lực"}
                </button>
                {fitnessSummary.length > 0 && (
                  <p className="mt-2 text-sm leading-relaxed text-slate-700">{fitnessSummary.join(" · ")}</p>
                )}
                {homeFoundation && testsFilled < 4 && (
                  <p className="mt-2 text-xs text-amber-700">
                    Cần đủ 4 ô (có thể là 0) để tạo lịch vừa sức.
                  </p>
                )}
              </div>
            )}

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">Ghi chú</label>
              <textarea
                className="field min-h-[88px] resize-y"
                maxLength={500}
                placeholder="Ví dụ: mới tập lại sau nghỉ dài, muốn tăng dần từ dễ…"
                value={healthNote}
                onChange={(e) => setHealthNote(e.target.value)}
              />
            </div>

            {!homeFoundation && (
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-600">
                Vùng cơ ưu tiên{" "}
                <span className="font-normal text-slate-400">(tuỳ chọn)</span>
              </label>
              <div className="flex flex-wrap gap-2">
                {focusOptsForGender(gender).map((o) => (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => toggleFocus(o.id)}
                    className={`chip ${focus.includes(o.id) ? "chip-active" : ""}`}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
            )}
          </div>
        )}

        {step === 3 && !homeFoundation && (
          <div className="space-y-5">
            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-600">Địa điểm tập</label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => selectLocation("home")}
                  className={`rounded-xl border py-2 font-semibold ${
                    location === "home" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200"
                  }`}
                >
                  Nhà
                </button>
                <button
                  type="button"
                  onClick={() => selectLocation("gym")}
                  className={`rounded-xl border py-2 font-semibold ${
                    location === "gym" ? "border-brand-500 bg-brand-50 text-brand-700" : "border-slate-200"
                  }`}
                >
                  Phòng gym
                </button>
              </div>
            </div>

            {location === "home" && (
              <div>
                <label className="mb-2 block text-sm font-semibold text-slate-600">Dụng cụ tại nhà</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => selectHomeEquipmentMode("none")}
                    className={`rounded-xl border px-3 py-2.5 text-sm font-semibold leading-snug ${
                      noEquipment
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 text-slate-600"
                    }`}
                  >
                    Không dụng cụ
                  </button>
                  <button
                    type="button"
                    onClick={() => selectHomeEquipmentMode("with")}
                    className={`rounded-xl border px-3 py-2.5 text-sm font-semibold leading-snug ${
                      !noEquipment
                        ? "border-brand-500 bg-brand-50 text-brand-700"
                        : "border-slate-200 text-slate-600"
                    }`}
                  >
                    Có dụng cụ
                  </button>
                </div>
                {!noEquipment && (
                  <p className="mt-2 text-xs text-slate-500">Chọn dụng cụ bạn đang có từ kho bên dưới.</p>
                )}
                {noEquipment && (
                  <>
                    <p className="mt-3 rounded-xl border border-rose-200 bg-rose-50 px-3 py-2.5 text-sm leading-relaxed text-rose-900">
                      <span className="font-bold">Lưu ý:</span> Việc tập tại nhà sẽ bị hạn chế, giảm hiệu quả và vô cùng
                      nhàm chán nếu không có dụng cụ hỗ trợ.
                    </p>
                    <Link
                      href="/mua-dung-cu"
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => saveAiBuilderDraft(captureDraft())}
                      className="mt-3 flex w-full items-center justify-center gap-2 rounded-xl bg-brand-500 px-4 py-3.5 text-sm font-bold text-white shadow-soft transition hover:bg-brand-600"
                    >
                      Tham khảo dụng cụ của TAPTOT
                      <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
                        <path d="M5 12h14M13 6l6 6-6 6" />
                      </svg>
                    </Link>
                  </>
                )}

                {!noEquipment && (
                  <>
                    <button
                      type="button"
                      onClick={() => setEquipModalOpen(true)}
                      className="mt-3 w-full rounded-xl border border-dashed border-brand-300 bg-brand-50/50 px-4 py-3 text-sm font-bold text-brand-700 hover:bg-brand-50"
                    >
                      {selectedWizardGroups.length
                        ? `Chọn lại từ kho dụng cụ (${selectedWizardGroups.length})`
                        : "Mở kho dụng cụ để chọn"}
                    </button>
                    {selectedWizardGroups.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        {selectedWizardGroups.map((group) => (
                          <button
                            key={group.id}
                            type="button"
                            onClick={() => removeEquipGroup(group.id)}
                            className="chip chip-active"
                            title="Bỏ chọn"
                          >
                            {group.label_vi} ×
                          </button>
                        ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        )}

        {(homeFoundation ? step === 4 : step === 5) && (
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">Bạn có bao nhiêu thời gian?</p>
              <div className="flex flex-row flex-wrap gap-2">
                {DURATION_OPTS.map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setSessionMinutes(m)}
                    className={`chip ${sessionMinutes === m ? "chip-active" : ""}`}
                  >
                    {m} phút
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-600">
                Số buổi mỗi tuần: {Math.min(sessionsPerWeek, maxSessions)}
              </label>
              <input
                type="range"
                min={2}
                max={maxSessions}
                value={Math.min(sessionsPerWeek, maxSessions)}
                onChange={(e) => setSessionsPerWeek(Number(e.target.value))}
                className="mt-2 w-full accent-brand-500"
              />
            </div>
          </div>
        )}

        <EquipmentPickerModal
          open={equipModalOpen}
          onClose={() => setEquipModalOpen(false)}
          selectedKeys={equipment}
          onSave={saveEquipment}
        />

        {step === 6 && !homeFoundation && (
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-600">
                Món ăn hay dùng <span className="font-normal text-slate-400">(để ráp thực đơn)</span>
              </label>
              <button
                type="button"
                disabled={aiSuggestFoods}
                onClick={() => setFoodModalOpen(true)}
                className="w-full rounded-xl border border-dashed border-brand-300 bg-brand-50/50 px-4 py-3 text-sm font-bold text-brand-700 hover:bg-brand-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {aiSuggestFoods
                  ? "TAPTOT chọn thịt, rau, cơm, khoai từ kho tươi"
                  : selectedFoodList.length
                    ? `Chọn lại món hay ăn (${selectedFoodList.length})`
                    : "Mở kho — chọn đạm, tinh bột, rau"}
              </button>
              {!aiSuggestFoods && (
                <div className="mt-2 grid grid-cols-3 gap-2">
                  {MEAL_ROLE_OPTS.map((role) => {
                    const n = roleCounts[role.id];
                    const ok = role.min === 0 || n >= role.min;
                    return (
                      <div
                        key={role.id}
                        className={`rounded-lg px-2 py-1.5 text-center text-xs ${
                          ok ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-800"
                        }`}
                      >
                        <span className="font-semibold">{role.label}</span>
                        <span className="ml-1">
                          {n}
                          {role.min > 0 ? `/${role.min}` : ""}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
              {!aiSuggestFoods && selectedFoodList.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2">
                  {selectedFoodList.map((f) => (
                    <button
                      key={f.id}
                      type="button"
                      onClick={() => removeFood(f.id)}
                      className="chip chip-active"
                      title="Bỏ chọn"
                    >
                      {foodDisplayName(f.name_vi)} ×
                    </button>
                  ))}
                </div>
              )}
              {!aiSuggestFoods && (
                <p className="mt-1.5 text-xs text-slate-400">
                  {MEAL_POOL_HELP} Đã chọn: {selectedFoodList.length} món.
                </p>
              )}
              <label className="mt-3 flex cursor-pointer items-start gap-2.5 rounded-xl border border-slate-100 bg-slate-50 px-3 py-3 text-sm text-slate-600 select-none">
                <input
                  type="checkbox"
                  checked={aiSuggestFoods}
                  onChange={(e) => {
                    const on = e.target.checked;
                    setAiSuggestFoods(on);
                    if (on) setErr("");
                  }}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-brand-500"
                />
                <span className="leading-snug">
                  Để TAPTOT chọn nguyên liệu tươi (thịt, rau, cơm, khoai). Bỏ tick nếu bạn muốn tự chọn món hay ăn.
                </span>
              </label>
            </div>
          </div>
        )}

        <FitnessTestModal
          open={fitnessOpen && (homeFoundation || location === "home")}
          onClose={() => setFitnessOpen(false)}
          values={{ pushups, pullups, plankSeconds, squats }}
          onSave={(next) => {
            setPushups(next.pushups);
            setPullups(next.pullups);
            setPlankSeconds(next.plankSeconds);
            setSquats(next.squats);
          }}
          presets={{
            pushups: PUSHUP_PRESETS,
            pullups: PULLUP_PRESETS,
            plankSeconds: PLANK_PRESETS,
            squats: SQUAT_PRESETS,
          }}
          tone={homeFoundation ? "beginner" : "default"}
        />

        <FoodPickerModal
          open={foodModalOpen}
          onClose={() => setFoodModalOpen(false)}
          selected={selectedFoods}
          onSave={saveFoods}
          showRoleFilters
        />

        <Modal
          open={accessGateOpen}
          onClose={() => setAccessGateOpen(false)}
          title="Mã lộ trình 100 ngày"
          size="lg"
        >
          <div className="p-5 sm:p-6">
            <div className="text-center">
              <p className="text-xs font-bold tracking-[0.18em] text-brand-600 uppercase">
                TAPTOT
              </p>
              <h2 className="mt-2 text-2xl font-extrabold tracking-tight text-slate-900">
                Bạn đã có mã trên tem chưa?
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500">
                Mỗi dụng cụ TAPTOT được tặng kèm một mã để tạo lịch tập và lịch ăn 100 ngày.
              </p>
            </div>

            <div className="mt-6 rounded-2xl border border-brand-200 bg-brand-50 p-5">
              <p className="font-extrabold text-brand-900">
                Chưa có mã? Chọn dụng cụ để bắt đầu
              </p>
              <p className="mt-1 text-sm leading-relaxed text-brand-800/80">
                Nhận hàng, tìm tem TAPTOT trên sản phẩm rồi quét mã để tiếp tục lộ trình này.
              </p>
              <p className="mt-3 text-xs font-bold text-brand-700">
                1 sản phẩm · 1 mã lộ trình 100 ngày
              </p>
              <Link
                href="/mua-dung-cu?from=challenge"
                onClick={() => saveAiBuilderDraft(captureDraft())}
                className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-brand-500 px-4 text-sm font-bold text-white transition hover:bg-brand-600"
              >
                Chọn dụng cụ phù hợp
              </Link>
            </div>

            <div className="my-6 flex items-center gap-3" aria-hidden>
              <span className="h-px flex-1 bg-slate-200" />
              <span className="text-xs font-bold tracking-wide text-slate-400 uppercase">
                Đã có mã
              </span>
              <span className="h-px flex-1 bg-slate-200" />
            </div>

            <label className="block text-sm font-bold text-slate-700" htmlFor="challenge-gift-code">
              Mã trên tem sản phẩm
            </label>
            <input
              id="challenge-gift-code"
              autoFocus
              inputMode="text"
              autoCapitalize="characters"
              autoCorrect="off"
              spellCheck={false}
              placeholder="TT-XXXX-XXXX"
              value={giftCode}
              onChange={(event) => {
                setGiftCode(formatGiftCodeInput(event.target.value));
                setGiftLookup(null);
                setGateCodeError("");
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  void submitGiftCode();
                }
              }}
              className="mt-2 w-full rounded-xl border border-slate-200 px-4 py-3.5 font-mono text-lg font-bold tracking-wide uppercase outline-none focus:border-brand-400 focus:ring-2 focus:ring-brand-100"
            />
            <div className="mt-2 min-h-5 text-sm" role="status" aria-live="polite">
              {giftChecking && <p className="text-slate-500">Đang kiểm tra mã…</p>}
              {!giftChecking && gateCodeError && (
                <p className="text-rose-600">{gateCodeError}</p>
              )}
              {!giftChecking && !gateCodeError && giftLookup?.valid && (
                <p className="font-semibold text-emerald-700">
                  Mã hợp lệ
                  {giftLookup.product_name_vi ? ` · ${giftLookup.product_name_vi}` : ""}.
                </p>
              )}
            </div>
            <button
              type="button"
              disabled={giftChecking}
              onClick={() => void submitGiftCode()}
              className="mt-4 min-h-12 w-full rounded-xl bg-slate-900 px-5 text-sm font-bold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {giftChecking ? "Đang kiểm tra…" : "Dùng mã và tiếp tục"}
            </button>
          </div>
        </Modal>

        <Modal
          open={confirmOpen}
          onClose={() => {
            setConfirmOpen(false);
            setAgeOk(false);
            setTermsOk(false);
          }}
          title="Nhận lịch"
          size="lg"
          lockScroll
        >
          <div className="flex max-h-[92vh] flex-col">
            <div className="min-h-0 flex-1 overflow-y-auto px-5 py-5">
            <p className="text-lg font-extrabold text-slate-900">Nhận lịch</p>
            <p className="mt-1 text-sm text-slate-500">
              Kiểm tra lại thông tin bên dưới, rồi tích hai ô xác nhận để nhận lịch.
            </p>
            <ul className="mt-4 space-y-2.5 rounded-xl border border-brand-100 bg-brand-50/70 px-4 py-3 text-sm">
              <ConfirmSummaryRow label="Thử thách" value={challengeSummary} />
              <ConfirmSummaryRow label="Mục tiêu" value={goalSummary} />
              <ConfirmSummaryRow label="Nơi tập" value={equipSummary} />
              <ConfirmSummaryRow label="Lịch tập" value={scheduleSummary} />
              {splitDays.length > 0 && (
                <ConfirmSummaryRow label="Các buổi trong tuần" value={splitDays.join(" → ")} />
              )}
              {focusLabels.length > 0 && (
                <ConfirmSummaryRow label="Vùng cơ ưu tiên" value={focusLabels.join(", ")} />
              )}
              {extraLabels.length > 0 && (
                <ConfirmSummaryRow label="Ưu tiên thêm" value={extraLabels.join(", ")} />
              )}
              <ConfirmSummaryRow label="Thực đơn" value={foodSummary} />
              {!homeFoundation && giftCode ? (
                <ConfirmSummaryRow label="Mã trên tem" value={giftSummary} />
              ) : null}
            </ul>
            {(
              l3WithoutTests ||
              healthLines.length > 0 ||
              beginnerHighFreq ||
              extraGoalLine ||
              sedentaryHighFreq
            ) && (
              <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
                {l3WithoutTests && (
                  <li>
                    Bạn chưa đủ 2 bài kiểm tra thể lực — lịch sẽ tính theo mức người tập 1–6 tháng.
                  </li>
                )}
                {healthLines.map((line) => (
                  <li key={line}>{line}</li>
                ))}
                {beginnerHighFreq && (
                  <li>
                    {sessionsPerWeek >= 6
                      ? "Bạn là người mới nhưng chọn 6 buổi/tuần: lịch tối đa 5 buổi, xen kẽ thân trên và thân dưới."
                      : "Bạn là người mới nhưng chọn 5 buổi/tuần: lịch sẽ xen kẽ thân trên, thân dưới và toàn thân."}
                  </li>
                )}
                {extraGoalLine && <li>{extraGoalLine}</li>}
                {sedentaryHighFreq && (
                  <li>
                    Bạn ít vận động ngày thường nhưng tập {sessionsPerWeek} buổi/tuần — hãy theo dõi
                    phục hồi và nghỉ khi mệt.
                  </li>
                )}
              </ul>
            )}
            </div>
            <div className="space-y-3 border-t border-slate-100 px-5 py-4">
              <TermsConsent
                idPrefix="ai-gen"
                ageOk={ageOk}
                termsOk={termsOk}
                onAgeOk={setAgeOk}
                onTermsOk={setTermsOk}
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setConfirmOpen(false);
                    setAgeOk(false);
                    setTermsOk(false);
                  }}
                  className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50"
                >
                  Chỉnh lại
                </button>
                <button
                  type="button"
                  onClick={() => void generate()}
                  disabled={loading || !termsAccepted(ageOk, termsOk)}
                  className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:opacity-50"
                >
                  Nhận lịch
                </button>
              </div>
            </div>
          </div>
        </Modal>

        {err && <p className="mt-4 text-sm text-rose-600">{err}</p>}

        <div className="mt-6 flex gap-2">
          {step > 1 && (
            <button
              type="button"
              onClick={() => {
                setErr("");
                setStep((s) => s - 1);
              }}
              className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50"
            >
              Quay lại
            </button>
          )}
          {step < wizardSteps.length ? (
            <button
              type="button"
              onClick={goNext}
              className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600"
            >
              Tiếp tục
            </button>
          ) : (
            <button
              type="button"
              onClick={requestConfirm}
              disabled={loading}
              className="flex-1 rounded-xl bg-brand-500 py-3.5 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Bắt đầu với TAPTOT
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
