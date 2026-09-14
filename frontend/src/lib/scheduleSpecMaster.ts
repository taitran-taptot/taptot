/** Spec lịch tập từ Google Sheet Master — sync với api/app/services/schedule_spec_master.py */

export type ExperienceKey = "0-1" | "1-6" | "6-24";
export type GenderKey = "male" | "female";
export type LocationKey = "gym" | "home";
export type HomeEquipKey = "with_equip" | "no_equip";

export const EXPERIENCE_OPTS: { key: ExperienceKey; label: string }[] = [
  { key: "0-1", label: "0–1 tháng" },
  { key: "1-6", label: "1–6 tháng" },
  { key: "6-24", label: "6–12 tháng" },
];

export const GENDER_OPTS: { key: GenderKey; label: string }[] = [
  { key: "male", label: "Nam" },
  { key: "female", label: "Nữ" },
];

export const LOCATION_OPTS: { key: LocationKey; label: string }[] = [
  { key: "gym", label: "Gym" },
  { key: "home", label: "Tại nhà" },
];

export const HOME_EQUIP_OPTS: { key: HomeEquipKey; label: string }[] = [
  { key: "with_equip", label: "Có dụng cụ" },
  { key: "no_equip", label: "Không dụng cụ" },
];

export const SESSIONS_OPTS = [2, 3, 4, 5, 6] as const;
export const DURATION_OPTS = [30, 45, 60, 75, 90] as const;

function weekCodeFor(opts: {
  experience: ExperienceKey;
  sessions: number;
  gender: GenderKey;
  location: LocationKey;
  homeEquip: HomeEquipKey;
}): string {
  const sess = Math.max(2, Math.min(6, opts.sessions)) as 2 | 3 | 4 | 5 | 6;
  const noEquip = opts.location === "home" && opts.homeEquip === "no_equip";
  const l1 = opts.experience === "0-1";
  const loaded = !noEquip;

    if (opts.gender === "male") {
      if (sess === 3) return loaded ? "PPL" : "ULU";
    if (loaded) {
      return { 2: "UL", 4: "ULUL", 5: "PPLUL", 6: "PPLPPL" }[sess];
    }
    return {
      2: "UL",
      4: "ULUL",
      5: "ULUL, Cardio-Core",
      6: "ULULUL",
    }[sess];
  }

  if (loaded) {
    return {
      2: "Lower, Upper",
      3: "LUL",
      4: "LPPL",
      5: "LULU, Cardio-Core",
      6: "Lower, Upper, Lower, Upper, Lower, Upper",
    }[sess];
  }
  if (l1) {
    return {
      2: "Lower, Upper",
      3: "LUL",
      4: "ULUL",
      5: "LULU, Cardio-Core",
      6: "Lower, Upper, Lower, Upper, Lower, Upper",
    }[sess];
  }
  return {
    2: "UL",
    3: "LUL",
    4: "ULUL",
    5: "LULU, Cardio-Core",
    6: "ULULUL",
  }[sess];
}

function buildWeekMatrix(): Record<string, string> {
  const out: Record<string, string> = {};
  for (const experience of ["0-1", "1-6", "6-24"] as const) {
    for (const sessions of [2, 3, 4, 5, 6] as const) {
      for (const gender of ["male", "female"] as const) {
        out[`${experience}|${sessions}|${gender}|gym`] = weekCodeFor({
          experience,
          sessions,
          gender,
          location: "gym",
          homeEquip: "with_equip",
        });
        for (const homeEquip of ["with_equip", "no_equip"] as const) {
          out[`${experience}|${sessions}|${gender}|home|${homeEquip}`] = weekCodeFor({
            experience,
            sessions,
            gender,
            location: "home",
            homeEquip,
          });
        }
      }
    }
  }
  return out;
}

/** Key: experience|sessions|gender|location|homeEquip(optional for gym) */
const WEEK_MATRIX: Record<string, string> = buildWeekMatrix();

export const SPLIT_LEGEND: { code: string; meaning: string }[] = [
  { code: "P / Push", meaning: "Ngực, vai, tay sau" },
  { code: "Pull", meaning: "Lưng, vai sau, tay trước" },
  { code: "L / Lower / Leg", meaning: "Chân – mông, đùi trước, đùi sau" },
  { code: "U / Upper", meaning: "Ngực, lưng, core" },
  { code: "FB / FullBody", meaning: "Ngực, lưng, core, chân" },
  { code: "Cardio-Core", meaning: "Buổi cardio + core" },
  { code: "UL", meaning: "Upper + Lower (2 buổi)" },
  { code: "ULU", meaning: "Upper + Lower + Upper (3 buổi, không dụng cụ)" },
  { code: "PPL", meaning: "Push + Pull + Legs (3 buổi)" },
  { code: "LUL", meaning: "Lower + Upper + Lower (3 buổi, ưu tiên chân)" },
  { code: "LULU", meaning: "Lower–Upper × 2 (4 buổi)" },
  { code: "LPPL", meaning: "Lower + Push + Pull + Legs (4 buổi)" },
  { code: "ULUL", meaning: "Upper–Lower × 2 (4 buổi)" },
  { code: "ULULUL", meaning: "Upper–Lower × 3 (6 buổi)" },
  { code: "PPLUL", meaning: "PPL + Upper + Lower (5 buổi)" },
  { code: "PPLPPL", meaning: "PPL × 2 (6 buổi)" },
];

export type GymSessionSpec = {
  minutes: number;
  warmup: string;
  lifting: string;
  cardio: string;
  cooldown: string;
  totalLifts: number;
  compounds: number;
  compoundSets: number;
  compoundRest: string;
  isolates: number;
  isolateSets: number;
  isolateRest: string;
};

export const GYM_SESSION_BY_MIN: Record<number, GymSessionSpec> = {
  30: {
    minutes: 30,
    warmup: "3p",
    lifting: "25p",
    cardio: "0",
    cooldown: "2p",
    totalLifts: 3,
    compounds: 1,
    compoundSets: 3,
    compoundRest: "2–3p",
    isolates: 2,
    isolateSets: 3,
    isolateRest: "1–2p",
  },
  45: {
    minutes: 45,
    warmup: "5p",
    lifting: "35p",
    cardio: "0",
    cooldown: "5p",
    totalLifts: 4,
    compounds: 2,
    compoundSets: 3,
    compoundRest: "2–3p",
    isolates: 2,
    isolateSets: 3,
    isolateRest: "1–2p",
  },
  60: {
    minutes: 60,
    warmup: "5p",
    lifting: "40p",
    cardio: "10p",
    cooldown: "5p",
    totalLifts: 5,
    compounds: 2,
    compoundSets: 3,
    compoundRest: "2–3p",
    isolates: 3,
    isolateSets: 3,
    isolateRest: "1–2p",
  },
  75: {
    minutes: 75,
    warmup: "10p",
    lifting: "45p",
    cardio: "15p",
    cooldown: "5p",
    totalLifts: 6,
    compounds: 2,
    compoundSets: 3,
    compoundRest: "2–3p",
    isolates: 4,
    isolateSets: 3,
    isolateRest: "1–2p",
  },
  90: {
    minutes: 90,
    warmup: "10p",
    lifting: "60p",
    cardio: "15p",
    cooldown: "5p",
    totalLifts: 7,
    compounds: 3,
    compoundSets: 3,
    compoundRest: "2–3p",
    isolates: 4,
    isolateSets: 3,
    isolateRest: "1–2p",
  },
};

export type HomeSessionSpec = {
  minutes: number;
  warmup: string;
  main: string;
  cooldown: string;
  resistanceCount: number;
  conditioningCount: number;
  conditioningMinutes: number;
  resistanceSets: number;
  resistanceRest: string;
  conditioningSets: number;
  conditioningRest: string;
};

export const HOME_SESSION_BY_MIN: Record<number, HomeSessionSpec> = {
  30: {
    minutes: 30,
    warmup: "3p",
    main: "25p",
    cooldown: "2p",
    resistanceCount: 2,
    conditioningCount: 1,
    conditioningMinutes: 5,
    resistanceSets: 3,
    resistanceRest: "2–3p",
    conditioningSets: 3,
    conditioningRest: "1–2p",
  },
  45: {
    minutes: 45,
    warmup: "5p",
    main: "35p",
    cooldown: "5p",
    resistanceCount: 3,
    conditioningCount: 1,
    conditioningMinutes: 8,
    resistanceSets: 3,
    resistanceRest: "2–3p",
    conditioningSets: 3,
    conditioningRest: "1–2p",
  },
  60: {
    minutes: 60,
    warmup: "5p",
    main: "40p",
    cooldown: "10p",
    resistanceCount: 4,
    conditioningCount: 1,
    conditioningMinutes: 10,
    resistanceSets: 3,
    resistanceRest: "2–3p",
    conditioningSets: 3,
    conditioningRest: "1–2p",
  },
  75: {
    minutes: 75,
    warmup: "10p",
    main: "55p",
    cooldown: "10p",
    resistanceCount: 5,
    conditioningCount: 1,
    conditioningMinutes: 15,
    resistanceSets: 3,
    resistanceRest: "2–3p",
    conditioningSets: 3,
    conditioningRest: "1–2p",
  },
  90: {
    minutes: 90,
    warmup: "10p",
    main: "70p",
    cooldown: "10p",
    resistanceCount: 6,
    conditioningCount: 1,
    conditioningMinutes: 20,
    resistanceSets: 3,
    resistanceRest: "2–3p",
    conditioningSets: 3,
    conditioningRest: "1–2p",
  },
};

export function lookupWeekSplit(opts: {
  experience: ExperienceKey;
  sessions: number;
  gender: GenderKey;
  location: LocationKey;
  homeEquip: HomeEquipKey;
}): string | null {
  const { experience, sessions, gender, location, homeEquip } = opts;
  const g = gender === "female" ? "female" : "male";
  const key =
    location === "gym"
      ? `${experience}|${sessions}|${g}|gym`
      : `${experience}|${sessions}|${g}|home|${homeEquip}`;
  return WEEK_MATRIX[key] ?? null;
}

function expandToken(token: string): string[] {
  const t = token.trim();
  if (!t) return [];
  if (/^FB\s*[×x]\s*2$/i.test(t)) return ["Full Body", "Full Body"];
  if (/^(PPL){2}$/i.test(t)) return ["Push", "Pull", "Legs", "Push", "Pull", "Legs"];
  if (/^PPLUL$/i.test(t)) return ["Push", "Pull", "Legs", "Upper", "Lower"];
  if (/^LPPL$/i.test(t)) return ["Lower", "Push", "Pull", "Legs"];
  if (/^LULU$/i.test(t)) return ["Lower", "Upper", "Lower", "Upper"];
  if (/^LUL$/i.test(t)) return ["Lower", "Upper", "Lower"];
  if (/^(UL){3}$/i.test(t)) return ["Upper", "Lower", "Upper", "Lower", "Upper", "Lower"];
  if (/^ULUL$/i.test(t)) return ["Upper", "Lower", "Upper", "Lower"];
  if (/^ULU$/i.test(t)) return ["Upper", "Lower", "Upper"];
  if (/^PPL$/i.test(t)) return ["Push", "Pull", "Legs"];
  if (/^UL$/i.test(t)) return ["Upper", "Lower"];
  if (/^FB$/i.test(t) || /^FullBody$/i.test(t)) return ["Full Body"];
  if (/^Leg$/i.test(t) || /^Legs$/i.test(t)) return ["Legs"];
  if (/^Lower$/i.test(t)) return ["Lower"];
  if (/^Upper$/i.test(t)) return ["Upper"];
  if (/^Push$/i.test(t)) return ["Push"];
  if (/^Pull$/i.test(t)) return ["Pull"];
  if (/^Cardio-Core$/i.test(t)) return ["Cardio-Core"];
  return [t];
}

/** Tách mã tuần thành danh sách buổi để hiển thị. */
export function expandWeekDays(code: string): string[] {
  const raw = code.replace(/\s+/g, " ").trim();
  if (!raw) return [];
  if (/^FB\s*[×x]\s*2$/i.test(raw)) return ["Full Body", "Full Body"];

  const parts = raw.includes(",")
    ? raw.split(",")
    : [raw];

  return parts.flatMap(expandToken);
}
