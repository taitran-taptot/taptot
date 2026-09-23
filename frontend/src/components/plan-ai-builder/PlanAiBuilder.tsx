"use client";

import { useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import {
  aiApi,
  type AiUsage,
  type FamiliarizationCatalog,
} from "@/lib/authApi";
import { isAuthenticated } from "@/lib/auth";
import { addGuestPlanToken } from "@/lib/guestPlans";
import {
  challengeQueryRequested,
  clearAiBuilderDraft,
  freshStartRequested,
  loadAiBuilderDraft,
  saveAiBuilderDraft,
  type AiBuilderDraft,
} from "@/lib/aiBuilderDraft";
import {
  ACTIVITY_FIELD_LABEL,
  ACTIVITY_OPTS,
  EXTRA_GOAL_OPTS,
  WEIGHT_GOAL_OPTS,
  bmiCategory,
  computeBmi,
  foundationBmiHint,
  foundationNutritionRecap,
  foundationWeightGoalCard,
  formatChallenge100DaysLabel,
  defaultGainKgPerWeek,
  defaultLossKgPerWeek,
  gainWeeklyKgOpts,
  lossWeeklyKgOpts,
  recommendedBmiChallengePace,
} from "@/lib/nutrition";
import type { Activity, ExtraGoal, Food, Gender, WeightGoal } from "@/lib/types";
import {
  collapsePublicEquipmentKeys,
  collapseToWizardEquipmentGroups,
  equipmentImageFitClass,
  PUBLIC_EQUIPMENT_LABELS,
  publicEquipmentImage,
  syncWizardEquipmentSelection,
  WIZARD_EQUIPMENT_GROUPS,
  wizardEquipmentGroupSelected,
  type WizardEquipmentGroup,
} from "@/lib/equipmentCatalog";
import { EQUIPMENT_GROUP_UI } from "@/lib/equipmentGroupUi";
import { mediaUrl, formatVnd } from "@/lib/labels";
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
import { FOUNDATION_WIZARD_INTRO } from "@/lib/directionTreeContent";
import BrandWordmark from "@/components/BrandWordmark";
import DirectionTree from "@/components/DirectionTree";
import FoodPickerModal from "@/components/FoodPickerModal";
import Modal from "@/components/Modal";
import TermsConsent, { termsAccepted } from "@/components/TermsConsent";
import ChallengeFitnessTestModal from "@/components/plan-ai-builder/ChallengeFitnessTestModal";
import {
  DEFAULT_DIRECTION_SELECTION,
  DIRECTION_COMING_SOON,
  directionLabel,
  isDirectionReady,
  selectionFromBuilderState,
  type ChallengeOffer,
  type DirectionSelection,
  type FamiliarizationPath,
} from "@/lib/directionTree";
import { countMealRoles, MEAL_POOL_HELP, MEAL_ROLE_OPTS, mealPoolReady } from "@/lib/mealPool";
import { foodDisplayName } from "@/lib/foodDisplay";
import { formatGiftCodeInput, giftCodeFromQuery, giftCodeReady, giftStartHref } from "@/lib/giftCode";
import { redeemCodeApi, type RedeemLookup } from "@/lib/shopApi";
import {
  challengePayApi,
  clearChallengeEntitlement,
  consumeChallengeGateContinue,
  loadChallengeEntitlement,
  markChallengeGateContinue,
  saveChallengeEntitlement,
} from "@/lib/challengePay";
import { CONTACT_HREF } from "@/lib/trainers";
import { beginFreshWizard } from "@/lib/fitness-tracker/session/results";
import {
  buildChallengeFitnessBaseline,
  challengeFitnessSummaryLines,
  challengeFitnessTests,
  challengeTestsComplete,
  kitFromWizardEquipment,
  type ChallengeTestDraft,
} from "@/lib/challengeFitnessTests";

const STEPS_100 = ["Hướng đi", "Cá nhân hóa", "Dụng cụ", "Trình độ", "Thời gian", "Thực đơn"];
const CHALLENGE_EQUIP_REQUIRED = "Hãy chọn một loại dụng cụ.";
const CHALLENGE_TESTS_REQUIRED = "Nhập đủ 4 bài kiểm tra thể lực trước khi tiếp tục.";

function wizardGroupImageSrc(slug: string): string | null {
  const path = publicEquipmentImage(slug);
  return path ? mediaUrl(path) : null;
}
const STEPS_FOUNDATION = [
  "Hướng đi",
  "Giới thiệu",
  "Cá nhân hóa",
  "Khái quát lịch tập và dinh dưỡng",
];
const FAMILIARIZATION_WEEKS = 9;
const FIRST_PUSH_PULL_WEEKS = 9;
const FIRST_PUSH_PULL_SESSIONS = 3;
const FIRST_PUSH_PULL_MINUTES = 45;

type DirectionMode = "challenge_100" | "familiarization";

const FALLBACK_FAMILIARIZATION_PATHS: FamiliarizationCatalog["paths"] = [
  {
    key: "first_push_pull",
    label_vi: "Nhập môn",
    description_vi:
      "60 ngày · 3 buổi/tuần. Học form đẩy–kéo, thích ứng gân khớp. Tường, ghế/bàn, balo, xà cửa.",
    target_level: "basic",
    duration_days: 60,
    duration_weeks: 9,
  },
  {
    key: "basic_foundation",
    label_vi: "Xây sức mạnh nền",
    description_vi:
      "60 ngày sau nhập môn. Chống đẩy sàn, kéo xà hoặc kéo người nằm, chuỗi sau. Balo 5–8 kg.",
    target_level: "basic",
    duration_days: 60,
    duration_weeks: 9,
  },
];

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
    time: ">6 tháng",
    who: "Biết điều chỉnh tạ, nghỉ ngơi và giữ form.",
    plan: "Lịch đầy đủ hơn, có phân nhóm cơ rõ.",
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

const MALE_FOCUS_OPTS = [
  { id: "nguc", label: "Ngực Săn" },
  { id: "bung", label: "6 Múi" },
  { id: "lung", label: "Lưng Rộng" },
  { id: "vai", label: "Vai Rộng" },
  { id: "chan", label: "Chân Săn" },
  { id: "eo", label: "Giảm Mỡ Bụng" },
  { id: "mo_lung", label: "Giảm Mỡ Lưng" },
  { id: "tay_to", label: "Tay To" },
];

const FEMALE_FOCUS_OPTS = [
  { id: "chan", label: "Chân Thon Gọn" },
  { id: "mong", label: "Mông Đầy Đặn" },
  { id: "eo", label: "Giảm Mỡ Bụng" },
  { id: "tay", label: "Tay Thon Gọn" },
  { id: "mo_lung", label: "Giảm Mỡ Lưng" },
  { id: "vai_thon", label: "Vai Thon Gọn" },
  { id: "nguc", label: "Ngực Săn" },
];

function focusOptsForGender(g: Gender | null) {
  return g === "female" ? FEMALE_FOCUS_OPTS : MALE_FOCUS_OPTS;
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

function experienceForFoundationPath(path: FamiliarizationPath): number {
  if (path === "first_push_pull") return 1;
  return 2;
}

function foundationEquipRecap(path: FamiliarizationPath): string {
  if (path === "first_push_pull") {
    return "Tường, ghế/bàn, balo từ tuần 1 · kéo người nằm tuần 3 · xà siết bả vai tuần 5.";
  }
  return "Thể trọng, xà đơn, ghế, balo 5–8 kg từ buổi 1.";
}

const GEN_STEPS = [
  { at: 0, label: "Phân tích thể lực & mục tiêu" },
  { at: 6, label: "Chọn bài tập phù hợp" },
  { at: 14, label: "Cân đối dinh dưỡng" },
  { at: 24, label: "Hoàn thiện lịch tuần" },
];
const GEN_STEPS_MEAL_FREE = [
  { at: 0, label: "Đánh giá tiêu chuẩn thể lực" },
  { at: 4, label: "Chọn bài tập phù hợp" },
  { at: 8, label: "Xếp lịch tập" },
  { at: 12, label: "Kiểm tra tải tập và phục hồi" },
];

// Overlay "đang tạo lịch" — chỉ thể hiện đang đợi, KHÔNG hiện vị trí / số thứ tự hàng chờ.
function GenerationOverlay({ elapsed, mealFree = false }: { elapsed: number; mealFree?: boolean }) {
  const steps = mealFree ? GEN_STEPS_MEAL_FREE : GEN_STEPS;
  const activeIdx = steps.reduce((acc, s, i) => (elapsed >= s.at ? i : acc), 0);
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
          {steps.map((s, i) => {
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
  stepperRef,
}: {
  step: number;
  onGo: (n: number) => void;
  steps: string[];
  stepperRef: RefObject<HTMLDivElement | null>;
}) {
  // Chỉ hiện bước Hướng đi lúc bắt đầu; sau Tiếp tục mới hiện toàn bộ tiến trình.
  const visible = step === 1 ? steps.slice(0, 1) : steps;
  return (
    <div
      ref={stepperRef}
      id="batdau-tien-trinh"
      className="mb-6 scroll-mt-28"
    >
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

export default function PlanAiBuilder({
  initialGiftCode = "",
  codeFromPath = false,
}: {
  initialGiftCode?: string;
  codeFromPath?: boolean;
} = {}) {
  const router = useRouter();
  const pathname = usePathname();
  const skipDurationSyncRef = useRef(false);
  const stepperRef = useRef<HTMLDivElement>(null);
  const shouldScrollToStepperRef = useRef(false);
  const [step, setStep] = useState(1);
  const [goal, setGoal] = useState<WeightGoal>("maintain");
  const [extraGoals, setExtraGoals] = useState<ExtraGoal[]>([]);
  const [gender, setGender] = useState<Gender | null>(null);
  const [age, setAge] = useState("25");
  const [height, setHeight] = useState("");
  const [weight, setWeight] = useState("");
  const [activity, setActivity] = useState<Activity>("moderate");
  const [experienceLevel, setExperienceLevel] = useState(1);
  const [durationWeeks, setDurationWeeks] = useState(FAMILIARIZATION_WEEKS);
  const [directionMode, setDirectionMode] = useState<DirectionMode>("familiarization");
  const [challengeOffer, setChallengeOffer] = useState<ChallengeOffer>("challenge_100");
  const [familiarizationPath, setFamiliarizationPath] =
    useState<FamiliarizationPath>("first_push_pull");
  const [directionSelection, setDirectionSelection] = useState<DirectionSelection>(
    DEFAULT_DIRECTION_SELECTION,
  );
  const challengeTab = directionMode === "challenge_100";
  const challenge100Days = challengeTab && challengeOffer === "challenge_100";
  const familiarization = directionMode === "familiarization";
  const skipRedeem = familiarization;
  const firstPushPull = familiarization && familiarizationPath === "first_push_pull";
  const wizardSteps = familiarization ? STEPS_FOUNDATION : STEPS_100;
  const [familiarizationCatalog, setFamiliarizationCatalog] =
    useState<FamiliarizationCatalog | null>(null);
  const [giftCode, setGiftCode] = useState("");
  const [giftLookup, setGiftLookup] = useState<RedeemLookup | null>(null);
  const [giftChecking, setGiftChecking] = useState(false);
  const [gateCodeError, setGateCodeError] = useState("");
  const [accessGateOpen, setAccessGateOpen] = useState(false);
  const [payEntitlement, setPayEntitlement] = useState("");
  const [payBusy, setPayBusy] = useState(false);
  const [payError, setPayError] = useState("");
  const [payStubId, setPayStubId] = useState("");
  const [pathCodeInvalid, setPathCodeInvalid] = useState(false);
  const [kgPerWeek, setKgPerWeek] = useState(() => defaultLossKgPerWeek(65));
  const [sessionsPerWeek, setSessionsPerWeek] = useState(3);
  const [sessionMinutes, setSessionMinutes] = useState(60);
  const [location, setLocation] = useState<"home" | "gym">("home");
  const [focus, setFocus] = useState<string[]>([]);
  const [equipment, setEquipment] = useState<string[]>(["pull-up-bar"]);
  const [equipLabels, setEquipLabels] = useState<Record<string, string>>({});
  /** Foundation drafts still store this; 100-day always requires a wizard group. */
  const [noEquipment, setNoEquipment] = useState(false);
  const [selectedFoods, setSelectedFoods] = useState<Record<number, Food>>({});
  const [foodModalOpen, setFoodModalOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [ageOk, setAgeOk] = useState(false);
  const [termsOk, setTermsOk] = useState(false);
  const [aiSuggestFoods, setAiSuggestFoods] = useState(false);
  const [pushups, setPushups] = useState("");
  const [kneePushups, setKneePushups] = useState("");
  const [pushupVariant, setPushupVariant] = useState("standard");
  const [pullups, setPullups] = useState("");
  const [pullTestVariant, setPullTestVariant] = useState("strict");
  const [pullHoldSeconds, setPullHoldSeconds] = useState("");
  const [invertedRows, setInvertedRows] = useState("");
  const [plankSeconds, setPlankSeconds] = useState("");
  const [squats, setSquats] = useState("");
  const [run10MinMeters, setRun10MinMeters] = useState("");
  const [dbPressReps, setDbPressReps] = useState("");
  const [dbPressKg, setDbPressKg] = useState("");
  const [dbRowReps, setDbRowReps] = useState("");
  const [dbRowKg, setDbRowKg] = useState("");
  const [gobletReps, setGobletReps] = useState("");
  const [gobletKg, setGobletKg] = useState("");
  const [bandLevel, setBandLevel] = useState("");
  const [healthNote, setHealthNote] = useState("");
  const [fitnessTestOpen, setFitnessTestOpen] = useState(false);
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
  const heightCm = Number.parseInt(height.trim(), 10);
  const statsReady =
    gender != null &&
    /^\d+$/.test(height.trim()) &&
    heightCm >= 50 &&
    heightCm <= 250 &&
    Number.isFinite(weightKg) &&
    weightKg >= 20 &&
    weightKg <= 400;
  const bmi = statsReady ? computeBmi(weightKg, heightCm) : null;
  const bmiMeta = bmi != null ? bmiCategory(bmi) : null;
  const ageYears = Number.parseInt(age.trim(), 10);
  const foundationGoalCard = useMemo(() => {
    if (!familiarization || !statsReady || gender == null || !Number.isFinite(ageYears)) return null;
    return foundationWeightGoalCard({
      gender,
      age: ageYears,
      heightCm,
      weightKg,
      activity,
    });
  }, [activity, ageYears, familiarization, gender, heightCm, statsReady, weightKg]);
  const mainChallengePicked = goal === "lose_weight" || goal === "gain_weight";
  const bmiPanelReady = !familiarization && statsReady && mainChallengePicked && bmi != null;
  const recommendedPace =
    bmiPanelReady && bmi != null ? recommendedBmiChallengePace(bmi, goal, weightKg) : null;
  const bmiPanelWasReady = useRef(false);

  useEffect(() => {
    if (!loading) return;
    const timer = setInterval(() => setGenElapsed((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [loading]);

  useEffect(() => {
    aiApi
      .usage()
      .then(setAiUsage)
      .catch(() => setAiUsage(null));
    aiApi
      .familiarizationCatalog()
      .then(setFamiliarizationCatalog)
      .catch(() => setFamiliarizationCatalog(null));
  }, []);

  const maxSessions = maxSessionsForLevel(experienceLevel);

  useEffect(() => {
    // Keep the persisted slider value inside the policy when experience changes.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setSessionsPerWeek((n) => {
      return Math.min(n, maxSessionsForLevel(experienceLevel));
    });
  }, [experienceLevel]);

  useEffect(() => {
    if (skipDurationSyncRef.current) {
      skipDurationSyncRef.current = false;
      return;
    }
    if (challenge100Days || challengeTab) return;
    if (familiarization) {
      // Direction changes own their fixed duration.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setDurationWeeks(FAMILIARIZATION_WEEKS);
      return;
    }
    setDurationWeeks(defaultDurationWeeks(experienceLevel));
  }, [experienceLevel, challenge100Days, challengeTab, familiarization]);

  useEffect(() => {
    const w = Number.isFinite(weightKg) && weightKg > 0 ? weightKg : 65;
    if (goal === "lose_weight") {
      const allowed = lossOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) {
        // Re-normalize after weight changes alter the safe choices.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setKgPerWeek(recommendedPace ?? defaultLossKgPerWeek(w));
      }
      return;
    }
    if (goal === "gain_weight") {
      const allowed = gainOpts.map((o) => o.value);
      if (!allowed.includes(kgPerWeek)) {
        setKgPerWeek(recommendedPace ?? defaultGainKgPerWeek(w));
      }
    }
  }, [goal, gainOpts, kgPerWeek, lossOpts, recommendedPace, weightKg]);

  useEffect(() => {
    if (bmiPanelReady && !bmiPanelWasReady.current && recommendedPace != null) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setKgPerWeek(recommendedPace);
    }
    bmiPanelWasReady.current = bmiPanelReady;
  }, [bmiPanelReady, recommendedPace]);

  useEffect(() => {
    let cancelled = false;
    const wantFresh = freshStartRequested();
    const draft = wantFresh ? null : loadAiBuilderDraft();
    const wantChallenge = challengeQueryRequested();
    const code = formatGiftCodeInput(initialGiftCode) || giftCodeFromQuery();
    const storedPay = loadChallengeEntitlement();
    const params = new URLSearchParams(window.location.search);
    const paidId = params.get("paid") || params.get("orderId") || "";
    const stubReturn = params.get("stub") === "1";
    // This effect hydrates state from external URL/sessionStorage sources once.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (storedPay) setPayEntitlement(storedPay);
    if (code) setGiftCode(code);
    if (code) {
      redeemCodeApi
        .lookup(code)
        .then((d) => {
          if (d.valid) {
            setGiftLookup(d);
            setPathCodeInvalid(false);
            setDirectionMode("challenge_100");
            setChallengeOffer("challenge_100");
            setDirectionSelection({ kind: "challenge", offer: "challenge_100" });
            setDurationWeeks(CHALLENGE_WEEKS);
            if (consumeChallengeGateContinue()) {
              goToStep(2);
            }
          } else if (codeFromPath) {
            setGiftLookup(d);
            setPathCodeInvalid(true);
          }
        })
        .catch(() => {
          if (codeFromPath) setPathCodeInvalid(true);
        });
    }
    if (paidId) {
      setDirectionMode("challenge_100");
      setChallengeOffer("challenge_100");
      setDirectionSelection({ kind: "challenge", offer: "challenge_100" });
      setDurationWeeks(CHALLENGE_WEEKS);
      if (stubReturn) setPayStubId(paidId);
      challengePayApi
        .status(paidId)
        .then(async (first) => {
          let status = first;
          if (status.stub && status.status !== "completed") {
            setPayStubId(paidId);
            setAccessGateOpen(true);
            return;
          }
          for (let i = 0; i < 12 && status.status === "pending"; i += 1) {
            await new Promise((resolve) => window.setTimeout(resolve, 2000));
            if (cancelled) return;
            status = await challengePayApi.status(paidId);
          }
          if (cancelled) return;
          if (status.status === "completed" && status.entitlement_token) {
            setPayEntitlement(status.entitlement_token);
            saveChallengeEntitlement(status.entitlement_token);
            goToStep(2);
            return;
          }
          if (status.status === "failed") {
            setPayError("Thanh toán không thành công. Thử lại.");
            setAccessGateOpen(true);
          }
        })
        .catch(() => {});
    }
    if (wantFresh) {
      const fields = beginFreshWizard();
      if (fields) {
        setPushups(fields.pushups);
        setPushupVariant(fields.pushupVariant);
        setPullups(fields.pullups);
        setPullTestVariant(fields.pullTestVariant);
        setPullHoldSeconds(fields.pullHoldSeconds);
        setPlankSeconds(fields.plankSeconds);
        setSquats(fields.squats);
        if (fields.run10MinMeters) setRun10MinMeters(fields.run10MinMeters);
      }
      params.delete("moi");
      const qs = params.toString();
      router.replace(`${pathname}${qs ? `?${qs}` : ""}`);
    } else if (draft) {
      skipDurationSyncRef.current = true;
      // eslint-disable-next-line react-hooks/immutability
      applyDraft(draft);
    } else if (wantChallenge) {
      setDirectionMode("challenge_100");
      setChallengeOffer("challenge_100");
      setDirectionSelection({ kind: "challenge", offer: "challenge_100" });
      setDurationWeeks(CHALLENGE_WEEKS);
    }
    if (wantChallenge && !wantFresh && !codeFromPath) {
      const qs = code ? `?code=${encodeURIComponent(code)}` : "";
      router.replace(`/batdau${qs}`);
    }
    return () => {
      cancelled = true;
    };
  }, [pathname, router, initialGiftCode, codeFromPath]);

  useEffect(() => {
    if (!shouldScrollToStepperRef.current) return;
    shouldScrollToStepperRef.current = false;
    const el = stepperRef.current;
    if (!el) return;
    const headerOffset = 112;
    const top = el.getBoundingClientRect().top + window.scrollY - headerOffset;
    window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
  }, [step]);

  async function submitGiftCode() {
    const formatted = formatGiftCodeInput(giftCode);
    if (!giftCodeReady(formatted)) {
      setGiftLookup(null);
      setGateCodeError("Mã không đúng");
      return;
    }
    setGiftChecking(true);
    setGateCodeError("");
    try {
      const result = await redeemCodeApi.lookup(formatted);
      setGiftLookup(result);
      if (!result.valid) {
        setGateCodeError("Mã không đúng");
        return;
      }
      setGiftCode(formatted);
      setAccessGateOpen(false);
      markChallengeGateContinue();
      saveAiBuilderDraft(captureDraft());
      const nextHref = giftStartHref(formatted);
      if (pathname !== nextHref && pathname !== decodeURIComponent(nextHref)) {
        router.push(nextHref);
        return;
      }
      goToStep(2);
    } catch {
      setGiftLookup({ valid: false, status: "invalid" });
      setGateCodeError("Mã không đúng");
    } finally {
      setGiftChecking(false);
    }
  }

  async function startMomoPay() {
    setPayError("");
    setPayBusy(true);
    try {
      const checkout = await challengePayApi.checkout();
      markChallengeGateContinue();
      saveAiBuilderDraft(captureDraft());
      if (checkout.stub) {
        setPayStubId(checkout.external_id);
        return;
      }
      window.location.assign(checkout.pay_url);
    } catch (ex) {
      setPayError((ex as Error).message);
    } finally {
      setPayBusy(false);
    }
  }

  async function finishStubPay() {
    if (!payStubId) return;
    setPayError("");
    setPayBusy(true);
    try {
      const status = await challengePayApi.simulate(payStubId);
      if (status.status === "completed" && status.entitlement_token) {
        setPayEntitlement(status.entitlement_token);
        saveChallengeEntitlement(status.entitlement_token);
        setAccessGateOpen(false);
        goToStep(2);
      } else {
        setPayError("Thanh toán chưa hoàn tất.");
      }
    } catch (ex) {
      setPayError((ex as Error).message);
    } finally {
      setPayBusy(false);
    }
  }

  function applyDraft(draft: AiBuilderDraft) {
    const draftFamiliarization = draft.direction === "familiarization";
    const offerReady = draftFamiliarization || draft.challengeOffer === "challenge_100";
    const maxStep = draftFamiliarization ? STEPS_FOUNDATION.length : STEPS_100.length;
    let restoredStep = Math.min(Math.max(Math.round(draft.step), 1), maxStep);
    if (draftFamiliarization && restoredStep >= 4) restoredStep = 4;
    setStep(offerReady ? restoredStep : 1);
    setGoal(
      draftFamiliarization
        ? "maintain"
        : draft.goal === "lose_weight" || draft.goal === "gain_weight"
          ? draft.goal
          : "maintain",
    );
    setExtraGoals(draft.extraGoals);
    setGender(draft.gender);
    setAge(draft.age);
    setHeight(draft.height);
    setWeight(draft.weight);
    setActivity(draft.activity);
    setExperienceLevel(
      draftFamiliarization
        ? experienceForFoundationPath(draft.familiarizationPath)
        : Math.min(Math.max(draft.experienceLevel, 1), 3),
    );
    setDirectionMode(draftFamiliarization ? "familiarization" : "challenge_100");
    setChallengeOffer(draft.challengeOffer);
    setFamiliarizationPath(draft.familiarizationPath);
    setDirectionSelection(
      selectionFromBuilderState(
        draftFamiliarization,
        draft.familiarizationPath,
        draft.challengeOffer,
      ),
    );
    setDurationWeeks(draftFamiliarization ? FAMILIARIZATION_WEEKS : CHALLENGE_WEEKS);
    setKgPerWeek(draft.kgPerWeek);
    setSessionsPerWeek(draft.sessionsPerWeek);
    setSessionMinutes(draft.sessionMinutes);
    setLocation(draftFamiliarization ? draft.location : "home");
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
    setNoEquipment(draftFamiliarization ? draft.noEquipment : false);
    setSelectedFoods(draft.selectedFoods);
    setAiSuggestFoods(draft.aiSuggestFoods);
    setPushups(draft.pushups);
    setKneePushups(draft.kneePushups || "");
    setPushupVariant(draft.pushupVariant);
    setPullups(draft.pullups);
    setPullTestVariant(draft.pullTestVariant);
    setPullHoldSeconds(draft.pullHoldSeconds);
    setInvertedRows(draft.invertedRows);
    setPlankSeconds(draft.plankSeconds);
    setSquats(draft.squats);
    setRun10MinMeters(draft.run10MinMeters);
    setDbPressReps(draft.dbPressReps || "");
    setDbPressKg(draft.dbPressKg || "");
    setDbRowReps(draft.dbRowReps || "");
    setDbRowKg(draft.dbRowKg || "");
    setGobletReps(draft.gobletReps || "");
    setGobletKg(draft.gobletKg || "");
    setBandLevel(draft.bandLevel || "");
    setHealthNote(draft.healthNote);
  }

  function captureDraft(): AiBuilderDraft {
    return {
      version: 2,
      step,
      direction: familiarization ? "familiarization" : "challenge",
      familiarizationPath,
      goal,
      extraGoals,
      gender: gender ?? "male",
      age,
      height,
      weight,
      activity,
      experienceLevel,
      durationWeeks,
      challenge100Days,
      challengeOffer,
      kgPerWeek,
      sessionsPerWeek,
      sessionMinutes,
      location: familiarization ? location : "home",
      focus,
      equipment: syncWizardEquipmentSelection(collapsePublicEquipmentKeys(equipment)),
      equipLabels,
      noEquipment: familiarization ? noEquipment : false,
      selectedFoods,
      aiSuggestFoods,
      pushups,
      kneePushups,
      pushupVariant,
      pullups,
      pullTestVariant,
      pullHoldSeconds,
      invertedRows,
      plankSeconds,
      squats,
      run10MinMeters,
      healthNote,
      testKit: kitFromWizardEquipment(equipment),
      dbPressReps,
      dbPressKg,
      dbRowReps,
      dbRowKg,
      gobletReps,
      gobletKg,
      bandLevel,
    };
  }

  function toggleFocus(id: string) {
    setFocus((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleExtraGoal(id: ExtraGoal) {
    setExtraGoals((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function selectWizardGroup(group: WizardEquipmentGroup) {
    setErr("");
    setNoEquipment(false);
    if (wizardEquipmentGroupSelected(equipment, group)) {
      setEquipment([]);
      return;
    }
    const nextKeys = syncWizardEquipmentSelection([...group.slugs]);
    setEquipment(nextKeys);
    setEquipLabels((prev) => {
      const next = { ...prev };
      for (const key of nextKeys) {
        next[key] =
          PUBLIC_EQUIPMENT_LABELS[key as keyof typeof PUBLIC_EQUIPMENT_LABELS] || group.label_vi;
      }
      return next;
    });
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
    if (!ACTIVITY_OPTS.some((o) => o.value === activity)) {
      return "Vui lòng chọn mức hoạt động hàng ngày.";
    }
    if (familiarization) return null;
    if (!MAIN_CHALLENGE_OPTS.some((o) => o.value === goal)) {
      return "Vui lòng chọn thử thách chính.";
    }
    const subOpts = goal === "gain_weight" ? gainOpts : lossOpts;
    if (!subOpts.some((o) => o.value === kgPerWeek)) {
      return "Vui lòng chọn thử thách phụ.";
    }
    return null;
  }

  function selectDirectionMode(mode: DirectionMode) {
    setDirectionMode(mode);
    setExtraGoals([]);
    if (mode === "challenge_100") {
      setChallengeOffer("challenge_100");
      setDurationWeeks(CHALLENGE_WEEKS);
      setLocation("home");
      setNoEquipment(false);
      setEquipment([]);
      return;
    }
    setDurationWeeks(FAMILIARIZATION_WEEKS);
    setLocation("home");
    setNoEquipment(false);
    setEquipment(["pull-up-bar"]);
    setAiSuggestFoods(false);
    setSelectedFoods({});
    setFocus([]);
    setExperienceLevel(1);
    setGoal("maintain");
  }

  function selectChallengeOffer(offer: ChallengeOffer) {
    setChallengeOffer(offer);
    setErr("");
    if (offer === "challenge_100") {
      setDurationWeeks(CHALLENGE_WEEKS);
      setLocation("home");
      setNoEquipment(false);
    }
  }

  function applyTreeSelection(next: DirectionSelection) {
    setDirectionSelection(next);
    setErr("");
    if (next.kind === "foundation") {
      if (directionMode !== "familiarization") {
        selectDirectionMode("familiarization");
      }
      setFamiliarizationPath(next.path);
      setExperienceLevel(experienceForFoundationPath(next.path));
      return;
    }
    if (next.kind === "challenge") {
      if (directionMode !== "challenge_100") {
        selectDirectionMode("challenge_100");
      }
      selectChallengeOffer(next.offer);
    }
  }

  function assertChallengeOfferReady(): boolean {
    if (isDirectionReady(directionSelection)) return true;
    setErr(DIRECTION_COMING_SOON);
    return false;
  }

  const testKit = useMemo(() => kitFromWizardEquipment(equipment), [equipment]);
  const challengeTestSpecs = useMemo(
    () => challengeFitnessTests({ kit: testKit, level: experienceLevel, gender }),
    [experienceLevel, gender, testKit],
  );
  const challengeTestDraft: ChallengeTestDraft = {
    pushups,
    kneePushups,
    pushupVariant,
    pullups,
    pullTestVariant,
    pullHoldSeconds,
    invertedRows,
    plankSeconds,
    squats,
    dbPressReps,
    dbPressKg,
    dbRowReps,
    dbRowKg,
    gobletReps,
    gobletKg,
    bandLevel,
  };

  const pullTestValue =
    pullTestVariant === "hang"
      ? pullHoldSeconds
      : pullTestVariant === "inverted_row" || pullTestVariant === "inverted_row_low"
        ? invertedRows
        : pullups;
  const testsComplete = challengeTestsComplete({
    kit: testKit,
    level: experienceLevel,
    gender,
    values: challengeTestDraft,
  });

  function goToStep(next: number | ((prev: number) => number)) {
    shouldScrollToStepperRef.current = true;
    setStep(next);
  }

  const challengeUnlocked =
    Boolean(giftLookup?.valid) || Boolean(payEntitlement);
  const laterStepUnlocked =
    skipRedeem || !REQUIRE_REDEEM_CODE || challengeUnlocked;

  function goNext() {
    setErr("");
    if (step === 1) {
      if (!assertChallengeOfferReady()) return;
      const needsCodeGate =
        REQUIRE_REDEEM_CODE &&
        directionSelection.kind === "challenge" &&
        !challengeUnlocked;
      if (needsCodeGate) {
        setGateCodeError("");
        setPayError("");
        setAccessGateOpen(true);
        return;
      }
      goToStep(2);
      return;
    }
    if (familiarization) {
      if (step === 2) {
        goToStep(3);
        return;
      }
      if (step === 3) {
        const msg = validatePersonalization();
        if (msg) {
          setErr(msg);
          return;
        }
        goToStep(4);
        return;
      }
      return;
    }
    if (step === 2) {
      const msg = validatePersonalization();
      if (msg) {
        setErr(msg);
        return;
      }
      goToStep(3);
      return;
    }
    if (!assertChallengeOfferReady()) {
      goToStep(1);
      return;
    }
    if (step === 3) {
      if (equipment.length === 0) {
        setErr(CHALLENGE_EQUIP_REQUIRED);
        return;
      }
      goToStep(4);
      return;
    }
    if (step === 4) {
      if (!testsComplete) {
        setErr(CHALLENGE_TESTS_REQUIRED);
        setFitnessTestOpen(true);
        return;
      }
      goToStep(5);
      return;
    }
    if (step === 5) {
      goToStep(6);
    }
  }

  function requestConfirm() {
    setErr("");
    if (!assertChallengeOfferReady()) {
      setConfirmOpen(false);
      setStep(1);
      return;
    }
    if (!laterStepUnlocked) {
      setConfirmOpen(false);
      setAccessGateOpen(true);
      return;
    }
    const msg = validatePersonalization();
    if (msg) {
      setErr(msg);
      setStep(familiarization ? 3 : 2);
      return;
    }
    if (!familiarization && equipment.length === 0) {
      setErr(CHALLENGE_EQUIP_REQUIRED);
      setStep(3);
      return;
    }
    if (!familiarization && !testsComplete) {
      setErr(CHALLENGE_TESTS_REQUIRED);
      setConfirmOpen(false);
      setStep(4);
      setFitnessTestOpen(true);
      return;
    }
    if (!familiarization && !aiSuggestFoods && !mealPoolReady(Object.values(selectedFoods))) {
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
    if (!assertChallengeOfferReady()) {
      setConfirmOpen(false);
      setStep(1);
      return;
    }
    if (!laterStepUnlocked) {
      setConfirmOpen(false);
      setAccessGateOpen(true);
      return;
    }
    const msg = validatePersonalization();
    if (msg) {
      setErr(msg);
      setStep(familiarization ? 3 : 2);
      return;
    }
    if (!familiarization && equipment.length === 0) {
      setErr(CHALLENGE_EQUIP_REQUIRED);
      setStep(3);
      return;
    }
    if (!familiarization && !testsComplete) {
      setErr(CHALLENGE_TESTS_REQUIRED);
      setConfirmOpen(false);
      setStep(4);
      setFitnessTestOpen(true);
      return;
    }
    if (!familiarization && !aiSuggestFoods && !mealPoolReady(Object.values(selectedFoods))) {
      setErr(MEAL_POOL_HELP);
      setStep(6);
      return;
    }
    setConfirmOpen(false);
    setGenElapsed(0);
    setLoading(true);
    try {
      const atHome = familiarization || location === "home";
      const homeNoEquip = !skipRedeem && atHome && noEquipment && !challenge100Days;
      const res = await aiApi.generateWorkout({
        goal: familiarization ? "maintain" : goal,
        gender: gender ?? "male",
        age: parseInt(age, 10),
        height_cm: parseFloat(height),
        weight_kg: parseFloat(weight),
        activity,
        sessions_per_week: familiarization ? FIRST_PUSH_PULL_SESSIONS : sessionsPerWeek,
        session_minutes: familiarization ? FIRST_PUSH_PULL_MINUTES : sessionMinutes,
        location: skipRedeem || challenge100Days ? "home" : location,
        focus_areas: skipRedeem ? [] : focus,
        extra_goals: challenge100Days || skipRedeem ? [] : extraGoals,
        equipment_list:
          firstPushPull
            ? []
            : familiarization
            ? ["pull-up-bar"]
            : atHome && !homeNoEquip
            ? syncWizardEquipmentSelection(collapsePublicEquipmentKeys(equipment))
            : [],
        food_ids: familiarization || aiSuggestFoods ? [] : Object.keys(selectedFoods).map(Number),
        experience_level: Math.min(Math.max(experienceLevel, 1), 3),
        ai_suggest_equipment: false,
        no_equipment: firstPushPull || homeNoEquip,
        ai_suggest_foods: familiarization ? false : aiSuggestFoods,
        fitness_baseline: atHome
          ? familiarization
            ? {
                pushup_variant: gender === "female" ? "knee" : "standard",
                pushups_max: 0,
                pull_test_variant: gender === "female" ? "hang" : "strict",
                pullups_max: 0,
                pull_hold_seconds: 0,
                inverted_rows_max: 0,
                squats_max: 0,
                plank_seconds: 0,
                run_10min_meters: 0,
              }
            : buildChallengeFitnessBaseline({
                kit: testKit,
                level: experienceLevel,
                gender,
                values: challengeTestDraft,
              })
          : {
              pushups_max: null,
              pullups_max: null,
              plank_seconds: null,
              squats_max: null,
            },
        health_note: null,
        duration_weeks: familiarization ? FIRST_PUSH_PULL_WEEKS : durationWeeks,
        kg_per_week:
          skipRedeem || (goal !== "lose_weight" && goal !== "gain_weight")
            ? undefined
            : kgPerWeek,
        challenge_100_days: challenge100Days || undefined,
        generation_mode: familiarization ? "familiarization" : undefined,
        familiarization_path: familiarization ? familiarizationPath : undefined,
        redeem_code: skipRedeem || payEntitlement ? undefined : giftCode || undefined,
        payment_entitlement: skipRedeem ? undefined : payEntitlement || undefined,
      });
      if (res.usage) setAiUsage(res.usage);
      const token = res.share_token;
      const viewPath = res.view_path || res.share_url_path || (token ? `/lich/${token}` : "");
      if (viewPath) {
        clearAiBuilderDraft();
        clearChallengeEntitlement();
        if (!isAuthenticated() && token) addGuestPlanToken(token);
        const tem = res.code_applied ? "&tem=1" : "";
        router.push(`${viewPath}?moi=1${tem}`);
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
  const familiarizationPaths =
    familiarizationCatalog?.paths ?? FALLBACK_FAMILIARIZATION_PATHS;
  const selectedFamiliarizationPath =
    familiarizationPaths.find((path) => path.key === familiarizationPath) ??
    FALLBACK_FAMILIARIZATION_PATHS[1];
  const fitnessSummary = familiarization
    ? ([
        pushups !== "" ? `Chống đẩy ${pushups} cái` : null,
        pullTestValue !== ""
          ? pullTestVariant === "hang"
            ? `Giữ người ${pullTestValue} giây`
            : pullTestVariant.startsWith("inverted_row")
              ? `Inverted row ${pullTestValue} cái`
              : `Kéo xà ${pullTestValue} cái`
          : null,
        plankSeconds !== "" ? `Plank ${plankSeconds} giây` : null,
        squats !== "" ? `Squat ${squats} cái` : null,
        run10MinMeters !== "" ? `Chạy 10 phút ${run10MinMeters} m` : null,
      ].filter(Boolean) as string[])
    : challengeFitnessSummaryLines(testKit, challengeTestDraft, gender, experienceLevel);
  const experienceCard = EXPERIENCE_CARDS.find((lv) => lv.value === experienceLevel);
  const sedentaryHighFreq =
    !skipRedeem && activity === "sedentary" && sessionsPerWeek >= 5;
  const focusLabels = focusOptsForGender(gender)
    .filter((o) => focus.includes(o.id))
    .map((o) => o.label);
  const clampedSessions = familiarization
    ? FIRST_PUSH_PULL_SESSIONS
    : Math.min(sessionsPerWeek, maxSessions);
  const beginnerHighFreq = experienceLevel <= 1 && clampedSessions >= 5;
  const selectedWizardGroups = useMemo(
    () => collapseToWizardEquipmentGroups(equipment),
    [equipment],
  );
  const equipSummary = firstPushPull
    ? "Nhà · tường, ghế/bàn, balo · kéo người nằm tuần 3 · xà tuần 5"
    : familiarization
    ? "Nhà · thể trọng, xà đơn, ghế, balo"
    : location === "gym"
      ? "Phòng gym"
      : selectedWizardGroups.length
        ? `Nhà · ${selectedWizardGroups.map((g) => g.label_vi).join(", ")}`
        : "Nhà · chưa chọn dụng cụ";
  const foodSummary = aiSuggestFoods
      ? "TAPTOT gợi ý thực đơn"
      : selectedFoodList.length
        ? `Bạn đã chọn ${selectedFoodList.length} món`
        : "Chưa chọn món";
  const nutritionSummary = foundationGoalCard?.summaryVi ?? "Nhập chiều cao, cân nặng và giới tính để xem calo.";
  const challengeSummary = (() => {
    const label = directionLabel(directionSelection);
    if (directionSelection.kind === "foundation") {
      return `${label} (60 ngày)`;
    }
    if (directionSelection.kind === "challenge" && directionSelection.offer === "challenge_100") {
      return `${label} (14 tuần)`;
    }
    return label;
  })();
  const splitCode = lookupWeekSplit({
    experience: levelToExperienceKey(experienceLevel),
    sessions: clampedSessions,
    gender: gender ?? "male",
    location: familiarization || challenge100Days ? "home" : location,
    homeEquip: firstPushPull ? "no_equip" : "with_equip",
  });
  const previewWeekCode =
    familiarization
      ? ""
      : beginnerHighFreq
        ? "Upper, Lower, Upper, Lower, Full Body"
        : splitCode;
  const splitDays = familiarization
    ? Array.from({ length: clampedSessions }, (_, index) => `Toàn thân ${index + 1}`)
    : previewWeekCode
      ? expandWeekDays(previewWeekCode).map((d) => WEEKDAY_VI[d] || d)
      : [];
  const goalSummary = familiarization
    ? selectedFamiliarizationPath.label_vi
    : goal === "lose_weight" || goal === "gain_weight"
      ? `${goalLabel} · ${formatChallenge100DaysLabel(goal, kgPerWeek)}`
      : goalLabel;
  const scheduleSummary = familiarization
    ? `60 ngày · ${FIRST_PUSH_PULL_SESSIONS} buổi/tuần · khoảng ${FIRST_PUSH_PULL_MINUTES} phút mỗi buổi`
    : `${Math.min(sessionsPerWeek, maxSessions)} buổi/tuần · ${sessionMinutes} phút mỗi buổi`;
  const giftSummary = giftCode
    ? giftLookup?.valid
      ? `${giftCode} · mã hợp lệ, dùng 1 lần khi tạo lịch`
      : `${giftCode} · mã không còn hiệu lực`
    : payEntitlement
      ? "Đã thanh toán MoMo"
      : "";
  const generatePrice = aiUsage?.generate_price_vnd || 49000;
  const roleCounts = countMealRoles(selectedFoodList);

  if (pathCodeInvalid) {
    return (
      <section className="mx-auto max-w-lg">
        <div className="rounded-2xl bg-white p-6 shadow-soft">
          <h1 className="type-display text-slate-900">Mã không đúng</h1>
          <p className="mt-2 text-sm leading-relaxed text-slate-500">
            Mã này đã được sử dụng hoặc không khớp mã trên tem. Kiểm tra lại tem hoặc thanh toán MoMo để mở lộ trình 100 ngày.
          </p>
          <a
            href="/batdau"
            className="mt-5 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-brand-500 px-4 text-sm font-bold text-white hover:bg-brand-600"
          >
            Nhập mã khác
          </a>
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      {loading && <GenerationOverlay elapsed={genElapsed} />}
      <div>
        <h1 className="type-display">Bắt đầu với <BrandWordmark /></h1>
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
        ) : payEntitlement ? (
          <div className="mt-3 rounded-xl bg-brand-50 px-3 py-2.5">
            <p className="text-sm text-brand-900">Đã thanh toán MoMo · mở khóa tạo lịch 100 ngày</p>
          </div>
        ) : null}
      </div>

      <div className="min-w-0 overflow-x-hidden rounded-2xl bg-white p-3 shadow-soft sm:p-5">
        <Stepper
          step={step}
          steps={wizardSteps}
          stepperRef={stepperRef}
          onGo={(n) => {
            setErr("");
            if (n > 1 && !assertChallengeOfferReady()) {
              goToStep(1);
              return;
            }
            if (n > 1 && !laterStepUnlocked) {
              setAccessGateOpen(true);
              return;
            }
            if (n > (familiarization ? 3 : 2)) {
              const msg = validatePersonalization();
              if (msg) {
                setErr(msg);
                goToStep(familiarization ? 3 : 2);
                return;
              }
            }
            if (!familiarization && n > 3 && equipment.length === 0) {
              setErr(CHALLENGE_EQUIP_REQUIRED);
              goToStep(3);
              return;
            }
            goToStep(n);
          }}
        />

        {step === 1 && (
          <DirectionTree
            selection={directionSelection}
            onSelect={applyTreeSelection}
            onContinue={goNext}
            catalog={familiarizationCatalog}
          />
        )}

        {familiarization && step === 2 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-brand-100 bg-brand-50/60 p-5">
              <p className="type-kicker text-brand-700">
                {FOUNDATION_WIZARD_INTRO[familiarizationPath].kicker}
              </p>
              <h2 className="mt-2 type-title text-slate-900">
                {FOUNDATION_WIZARD_INTRO[familiarizationPath].title}
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600">
                {FOUNDATION_WIZARD_INTRO[familiarizationPath].body}
              </p>
              <ul className="mt-4 space-y-2 text-sm text-slate-700">
                {FOUNDATION_WIZARD_INTRO[familiarizationPath].bullets.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
              <p className="mt-4 text-xs leading-relaxed text-slate-500">
                {FOUNDATION_WIZARD_INTRO[familiarizationPath].note}
              </p>
            </div>
          </div>
        )}

        {((familiarization && step === 3) || (!familiarization && step === 2)) && (
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
                        if (g === "male") {
                          setPushupVariant("standard");
                          setPullTestVariant("strict");
                        }
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
                  {ACTIVITY_OPTS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </div>
              {!familiarization ? (
                <div className="mt-3">
                  <label className="mb-1.5 block text-sm font-semibold text-slate-600" htmlFor="ai-experience">
                    Kinh nghiệm tập luyện
                  </label>
                  <select
                    id="ai-experience"
                    className="field"
                    value={experienceLevel}
                    onChange={(e) => setExperienceLevel(Number(e.target.value))}
                  >
                    {EXPERIENCE_CARDS.map((lv) => (
                      <option key={lv.value} value={lv.value}>
                        {`${lv.label} (${lv.time})`}
                      </option>
                    ))}
                  </select>
                </div>
              ) : null}
            </div>

            {statsReady && bmiMeta && bmi != null ? (
              <div className={`rounded-2xl p-4 ${bmiMeta.bg}`}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="type-kicker text-slate-500">
                      Chỉ số BMI
                    </p>
                    <p className={`mt-1 text-3xl leading-none font-bold ${bmiMeta.cls}`}>
                      {String(bmi).replace(".", ",")}
                    </p>
                  </div>
                  <span
                    className={`rounded-full bg-white px-3 py-1.5 text-center text-sm font-semibold ${bmiMeta.cls}`}
                  >
                    {bmiMeta.vi}
                  </span>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-slate-600">{bmiMeta.advice}</p>
                {familiarization ? (
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {foundationBmiHint(bmiMeta.key)}
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
                Nhập chiều cao, cân nặng và giới tính để xem BMI.
              </p>
            )}

            {bmiMeta?.key === "obese_2" ? (
              <p className="rounded-xl border border-rose-200 bg-rose-50 px-3 py-3 text-sm text-rose-800">
                BMI đang ở mức béo phì độ II trở lên. Nên{" "}
                <Link href={CONTACT_HREF} className="font-semibold underline decoration-rose-300 underline-offset-2 hover:text-rose-950">
                  tìm huấn luyện viên
                </Link>{" "}
                để được theo dõi sát. Bạn vẫn có thể tiếp tục nếu muốn.
              </p>
            ) : null}

            {familiarization ? (
              <div className="rounded-xl border border-brand-100 bg-brand-50/60 p-4">
                <p className="type-kicker text-brand-700">
                  Lộ trình đã chọn
                </p>
                <p className="mt-1 font-bold text-slate-900">
                  {selectedFamiliarizationPath.label_vi}
                </p>
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
                          const nextBmi = statsReady ? computeBmi(w, heightCm) : null;
                          const suggested =
                            nextBmi != null
                              ? recommendedBmiChallengePace(nextBmi, o.value, w)
                              : null;
                          if (suggested != null) setKgPerWeek(suggested);
                          else if (o.value === "lose_weight") setKgPerWeek(defaultLossKgPerWeek(w));
                          else setKgPerWeek(defaultGainKgPerWeek(w));
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

                {!bmiPanelReady ? (
                  <p className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
                    Chọn thử thách chính để xem gợi ý tốc độ.
                  </p>
                ) : (
                  <div className="space-y-3">
                    {bmiMeta?.key === "underweight" && goal === "lose_weight" ? (
                      <p className="rounded-xl border border-amber-200 bg-amber-50 px-3 py-3 text-sm text-amber-800">
                        BMI đang ở mức thiếu cân. Giảm tiếp có thể ảnh hưởng sức khỏe. Bạn vẫn có thể tiếp tục nếu muốn.
                      </p>
                    ) : null}

                    <div>
                      <label className="mb-1.5 block text-sm font-semibold text-slate-600">Thử thách phụ</label>
                      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                        {(goal === "gain_weight" ? gainOpts : lossOpts).map((o) => {
                          const subKind = goal === "gain_weight" ? "gain_weight" : "lose_weight";
                          const suggested = recommendedPace != null && o.value === recommendedPace;
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
                              <span className="block text-sm font-bold leading-snug tracking-tight sm:text-[15px]">
                                {formatChallenge100DaysLabel(subKind, o.value)}
                              </span>
                              {suggested ? (
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
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {!familiarization && step === 4 && (
          <div className="space-y-5">
            <div>
              <p className="type-kicker text-brand-600">Trình độ</p>
              <h2 className="mt-0.5 text-base font-bold text-slate-900 sm:text-lg">
                Kiểm tra thể lực
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Bốn bài khớp dụng cụ bạn đã chọn. Nhập đủ 4 bài trước khi tiếp tục.
              </p>
              <button
                type="button"
                onClick={() => setFitnessTestOpen(true)}
                className="mt-3 w-full rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600"
              >
                Kiểm tra thể lực
              </button>
              {fitnessSummary.length > 0 ? (
                <ul className="mt-3 space-y-1 rounded-xl bg-slate-50 px-3 py-3 text-sm text-slate-600">
                  {fitnessSummary.map((line) => (
                    <li key={line}>{line}</li>
                  ))}
                </ul>
              ) : null}
              {!testsComplete ? (
                <p className="mt-2 text-xs text-rose-500">Chưa nhập đủ 4 bài test.</p>
              ) : null}
            </div>

            <ChallengeFitnessTestModal
              open={fitnessTestOpen}
              onClose={() => setFitnessTestOpen(false)}
              tests={challengeTestSpecs}
              values={challengeTestDraft}
              onSave={(next) => {
                setPushups(next.pushups);
                setKneePushups(next.kneePushups);
                setPushupVariant(next.pushupVariant);
                setPullups(next.pullups);
                setPullTestVariant(next.pullTestVariant);
                setPullHoldSeconds(next.pullHoldSeconds);
                setInvertedRows(next.invertedRows);
                setPlankSeconds(next.plankSeconds);
                setSquats(next.squats);
                setDbPressReps(next.dbPressReps);
                setDbPressKg(next.dbPressKg);
                setDbRowReps(next.dbRowReps);
                setDbRowKg(next.dbRowKg);
                setGobletReps(next.gobletReps);
                setGobletKg(next.gobletKg);
                setBandLevel(next.bandLevel);
              }}
            />

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
          </div>
        )}

        {step === 3 && !familiarization && (
          <div className="space-y-4">
            <div>
              <p className="type-kicker text-brand-600">Dụng cụ tại nhà</p>
              <h2 className="mt-0.5 text-base font-bold text-slate-900 sm:text-lg">
                Bạn đang có dụng cụ nào?
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Chạm để chọn <b className="text-brand-600">1</b> loại dụng cụ
              </p>
            </div>
            <ul className="flex flex-col gap-3">
              {WIZARD_EQUIPMENT_GROUPS.map((group) => {
                const on = wizardEquipmentGroupSelected(equipment, group);
                const dual = Boolean(group.products && group.products.length >= 2);
                const ui = EQUIPMENT_GROUP_UI[group.id];
                return (
                  <li key={group.id}>
                    <button
                      type="button"
                      onClick={() => selectWizardGroup(group)}
                      aria-pressed={on}
                      className={`relative flex w-full items-center gap-3 overflow-hidden rounded-2xl border px-3 py-3 text-left transition ${
                        on
                          ? ui.cardSelected
                          : `border-slate-200 bg-white ${ui.cardHover}`
                      }`}
                    >
                      <span
                        className={`absolute inset-y-0 left-0 w-1 ${ui.accentBar}`}
                        aria-hidden
                      />
                      {dual ? (
                        <span
                          className={`flex h-[4.5rem] w-[6.75rem] shrink-0 items-center gap-1 rounded-xl p-1 ring-1 sm:h-20 sm:w-[7.25rem] ${
                            on ? ui.tintSelected : ui.tint
                          }`}
                        >
                          {group.products!.map((product, idx) => {
                            const src = wizardGroupImageSrc(product.slug);
                            return (
                              <span key={product.slug} className="contents">
                                {idx > 0 && (
                                  <span className="text-[10px] font-bold text-slate-400" aria-hidden>
                                    +
                                  </span>
                                )}
                                <span className="grid h-full flex-1 place-items-center rounded-lg bg-white/70">
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
                          className={`grid h-[4.5rem] w-[4.5rem] shrink-0 place-items-center rounded-xl ring-1 sm:h-20 sm:w-20 ${
                            on ? ui.tintSelected : ui.tint
                          }`}
                        >
                          {(() => {
                            const slug = group.slugs[0];
                            const src = wizardGroupImageSrc(slug);
                            return src ? (
                              // eslint-disable-next-line @next/next/no-img-element
                              <img
                                src={src}
                                alt=""
                                className={`max-h-[88%] max-w-[88%] ${equipmentImageFitClass(slug)}`}
                              />
                            ) : (
                              <span className="text-xs text-slate-400">—</span>
                            );
                          })()}
                        </span>
                      )}

                      <span className="min-w-0 flex-1 pr-1">
                        <span className="flex flex-wrap items-center gap-1.5">
                          <span className={`badge ${ui.badge}`}>{ui.difficulty}</span>
                        </span>
                        <span className="mt-1.5 block text-[15px] font-bold leading-snug text-slate-900">
                          {group.label_vi}
                        </span>
                        <span className="mt-0.5 block text-xs leading-relaxed text-slate-500">
                          {ui.hint}
                        </span>
                      </span>

                      <span
                        className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold transition ${
                          on ? ui.checkSelected : "bg-white text-transparent ring-2 ring-slate-300"
                        }`}
                        aria-hidden
                      >
                        ✓
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        {familiarization && step === 4 && (
          <div className="space-y-4">
            <div className="rounded-2xl border border-brand-100 bg-brand-50/60 p-5">
              <p className="type-kicker text-brand-700">
                Lịch tập
              </p>
              <h2 className="mt-2 type-title text-slate-900">
                60 ngày · 3 buổi mỗi tuần
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-slate-600">
                Mỗi buổi khoảng 45 phút. Các ngày còn lại là ngày nghỉ phục hồi và được
                ghi rõ trong lịch. Bạn không cần chọn ngày, giờ hoặc số buổi.
              </p>
              <p className="mt-3 rounded-xl bg-white px-3 py-2 text-sm font-semibold text-slate-700">
                {foundationEquipRecap(familiarizationPath)}
              </p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="type-kicker text-slate-500">
                Dinh dưỡng
              </p>
              <h2 className="mt-2 type-title text-slate-900">
                {foundationGoalCard?.title ?? (bmiMeta ? foundationNutritionRecap(bmiMeta.key).title : "Hướng ăn theo BMI")}
              </h2>
              {bmiMeta ? (
                <p className="mt-3 text-sm leading-relaxed text-slate-600">
                  {foundationNutritionRecap(bmiMeta.key).body} {foundationBmiHint(bmiMeta.key)}
                </p>
              ) : (
                <p className="mt-3 text-sm leading-relaxed text-slate-600">
                  Nhập chiều cao, cân nặng và giới tính ở bước Cá nhân hóa để xem hướng ăn.
                </p>
              )}
              {foundationGoalCard ? (
                <div className="mt-4 rounded-xl bg-slate-50 px-4 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                    Calo cần ăn mỗi ngày
                  </p>
                  <p className="mt-1 text-3xl font-bold tabular-nums text-slate-900">
                    {foundationGoalCard.dailyKcal.toLocaleString("vi-VN")}
                    <span className="ml-1 text-base font-semibold text-slate-500">kcal</span>
                  </p>
                  <p className="mt-1 text-sm text-slate-600">
                    Đạm khoảng {foundationGoalCard.proteinG.toLocaleString("vi-VN")} g
                  </p>
                  <p className="mt-3 text-sm leading-relaxed text-slate-700">
                    {foundationGoalCard.currentKg.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} kg
                    {" → "}
                    {foundationGoalCard.targetKg.toLocaleString("vi-VN", { maximumFractionDigits: 1 })} kg
                    {" · BMI "}
                    {String(foundationGoalCard.targetBmi).replace(".", ",")}
                    {" trong 2 tháng"}
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-slate-500">
                    Hướng về BMI bình thường 18,5–22,9. Lịch 2 tháng dùng tốc độ an toàn, chưa nhất
                    thiết tới đúng mốc đó.
                  </p>
                </div>
              ) : null}
            </div>
          </div>
        )}

        {!familiarization && step === 5 && (
          <div className="space-y-5">
            <div>
              <p className="mb-2 text-sm font-semibold text-slate-600">
                Bạn có bao nhiêu thời gian?
              </p>
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

        {!familiarization && step === 6 && (
          <div className="space-y-5">
            <div>
              <label className="mb-2 block text-sm font-semibold text-slate-600">
                Món ăn hay dùng{" "}
                <span className="font-normal text-slate-400">
                  (để ráp thực đơn)
                </span>
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
          title="Mở lộ trình 100 ngày"
          size="lg"
        >
          <div className="p-5 sm:p-6">
            <div className="text-center">
              <p className="type-kicker text-brand-600">
                <BrandWordmark className="" />
              </p>
              <h2 className="mt-2 type-display text-slate-900">Nhập mã hoặc thanh toán MoMo</h2>
              <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-slate-500">
                Dùng mã trên tem sản phẩm, hoặc thanh toán một lần để tạo lịch tập và lịch ăn 100 ngày.
              </p>
            </div>

            <label className="mt-6 block text-sm font-bold text-slate-700" htmlFor="challenge-gift-code">
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
              disabled={giftChecking || payBusy}
              onClick={() => void submitGiftCode()}
              className="mt-4 min-h-12 w-full rounded-xl bg-slate-900 px-5 text-sm font-bold text-white transition hover:bg-slate-700 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
            >
              {giftChecking ? "Đang kiểm tra…" : "Dùng mã và tiếp tục"}
            </button>

            <div className="my-6 flex items-center gap-3" aria-hidden>
              <span className="h-px flex-1 bg-slate-200" />
              <span className="type-kicker text-slate-400">hoặc</span>
              <span className="h-px flex-1 bg-slate-200" />
            </div>

            <div className="rounded-2xl border border-brand-200 bg-brand-50 p-5">
              <p className="font-bold text-brand-900">Thanh toán MoMo</p>
              <p className="mt-1 text-sm leading-relaxed text-brand-800/80">
                {formatVnd(generatePrice)} · một lần, mở khóa tạo lịch 100 ngày.
              </p>
              {payError ? <p className="mt-2 text-sm text-rose-600">{payError}</p> : null}
              {payStubId ? (
                <button
                  type="button"
                  disabled={payBusy}
                  onClick={() => void finishStubPay()}
                  className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-brand-500 px-4 text-sm font-bold text-white transition hover:bg-brand-600 disabled:opacity-50"
                >
                  {payBusy ? "Đang xác nhận…" : "Hoàn tất thanh toán thử"}
                </button>
              ) : (
                <button
                  type="button"
                  disabled={payBusy || giftChecking}
                  onClick={() => void startMomoPay()}
                  className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-brand-500 px-4 text-sm font-bold text-white transition hover:bg-brand-600 disabled:opacity-50"
                >
                  {payBusy ? "Đang mở MoMo…" : "Thanh toán bằng MoMo"}
                </button>
              )}
            </div>
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
            <p className="text-lg font-bold text-slate-900">Nhận lịch</p>
            <p className="mt-1 text-sm text-slate-500">
              Kiểm tra lại thông tin bên dưới, rồi tích hai ô xác nhận để nhận lịch.
            </p>
            <ul className="mt-4 space-y-2.5 rounded-xl border border-brand-100 bg-brand-50/70 px-4 py-3 text-sm">
              <ConfirmSummaryRow label="Hướng đi" value={challengeSummary} />
              <ConfirmSummaryRow label="Mục tiêu" value={goalSummary} />
              <ConfirmSummaryRow
                label={familiarization ? "Nơi tập" : "Dụng cụ"}
                value={equipSummary}
              />
              <ConfirmSummaryRow label="Lịch tập" value={scheduleSummary} />
              {!familiarization ? (
                <ConfirmSummaryRow
                  label="Kinh nghiệm"
                  value={
                    experienceCard
                      ? `${experienceCard.label} (${experienceCard.time})`
                      : String(experienceLevel)
                  }
                />
              ) : null}
              {fitnessSummary.length > 0 ? (
                <ConfirmSummaryRow label="Thể lực" value={fitnessSummary.join(" · ")} />
              ) : null}
              {splitDays.length > 0 && (
                <ConfirmSummaryRow label="Các buổi trong tuần" value={splitDays.join(" → ")} />
              )}
              {focusLabels.length > 0 && (
                <ConfirmSummaryRow label="Vùng cơ ưu tiên" value={focusLabels.join(", ")} />
              )}
              {extraLabels.length > 0 && (
                <ConfirmSummaryRow label="Ưu tiên thêm" value={extraLabels.join(", ")} />
              )}
              <ConfirmSummaryRow
                label={familiarization ? "Dinh dưỡng" : "Thực đơn"}
                value={familiarization ? nutritionSummary : foodSummary}
              />
              {!familiarization && (giftCode || payEntitlement) ? (
                <ConfirmSummaryRow label="Mã trên tem" value={giftSummary} />
              ) : null}
            </ul>
            {(
              beginnerHighFreq ||
              extraGoalLine ||
              sedentaryHighFreq
            ) && (
              <ul className="mt-3 space-y-1.5 text-sm text-slate-600">
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

        {step > 1 ? (
          <div className="mt-6 flex gap-2">
            <button
              type="button"
              onClick={() => {
                setErr("");
                goToStep((s) => s - 1);
              }}
              className="rounded-xl border border-slate-200 px-5 py-3 text-sm font-bold text-slate-600 hover:bg-slate-50"
            >
              Quay lại
            </button>
            {step < wizardSteps.length ? (
              <button
                type="button"
                onClick={goNext}
                disabled={!familiarization && step === 4 && !testsComplete}
                className="flex-1 rounded-xl bg-brand-500 py-3 text-sm font-bold text-white hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-slate-200 disabled:text-slate-500"
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
        ) : null}
      </div>
    </section>
  );
}
