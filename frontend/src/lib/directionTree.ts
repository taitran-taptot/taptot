export type FamiliarizationPath =
  | "first_push_pull"
  | "basic_foundation"
  | "advanced_foundation";

export type ChallengeOffer = "challenge_100" | "fitness_advanced";

export function isAdvancedFitnessOffer(raw: string | null | undefined): boolean {
  return raw === "fitness_advanced" || raw === "fitness_soldier";
}

export function normalizeChallengeOffer(raw: string | null | undefined): ChallengeOffer {
  return isAdvancedFitnessOffer(raw) ? "fitness_advanced" : "challenge_100";
}

export type SpecializationBranchKey =
  | "gym"
  | "calisthenic"
  | "martial"
  | "sport"
  | "other"
  | "hybrid";

export type DirectionSelection =
  | { kind: "foundation"; path: FamiliarizationPath }
  | { kind: "challenge"; offer: ChallengeOffer }
  | { kind: "specialization"; branch: SpecializationBranchKey; leaf?: string };

export const FOUNDATION_NODES: {
  key: FamiliarizationPath;
  label_vi: string;
  blurb_vi: string;
  meta_vi: string;
}[] = [
  {
    key: "first_push_pull",
    label_vi: "Nhập môn",
    blurb_vi: "Học form đẩy–kéo, thích ứng gân khớp",
    meta_vi: "60 ngày · 3 buổi/tuần",
  },
  {
    key: "basic_foundation",
    label_vi: "Xây sức mạnh nền",
    blurb_vi: "Tăng lực đẩy/kéo và hoàn thiện chuỗi sau",
    meta_vi: "60 ngày · 3 buổi/tuần",
  },
  {
    key: "advanced_foundation",
    label_vi: "Nền tảng nâng cao",
    blurb_vi: "Sức mạnh tương đối, sẵn sàng chơi thể thao",
    meta_vi: "60 ngày · 3 buổi/tuần",
  },
];

export const CHALLENGE_BRANCHES: {
  key: ChallengeOffer;
  parent: FamiliarizationPath;
  label_vi: string;
  short_vi: string;
  ready: boolean;
}[] = [
  {
    key: "challenge_100",
    parent: "basic_foundation",
    label_vi: "Thử thách 100 ngày thay đổi cơ thể",
    short_vi: "100 ngày thay đổi",
    ready: true,
  },
  {
    key: "fitness_advanced",
    parent: "advanced_foundation",
    label_vi: "Thử thách thể lực nâng cao",
    short_vi: "Thể lực nâng cao",
    ready: true,
  },
];

export const SPECIALIZATION_BRANCHES: {
  key: SpecializationBranchKey;
  label_vi: string;
  label_en?: string;
  leaves: { id: string; label_vi: string; label_en?: string }[];
}[] = [
  {
    key: "gym",
    label_vi: "Gym / Thể hình",
    leaves: [
      { id: "hypertrophy", label_vi: "Tăng phì đại cơ bắp", label_en: "Hypertrophy" },
      { id: "maximal_strength", label_vi: "Sức mạnh cực đại / Powerlifting", label_en: "Maximal Strength" },
      { id: "olympic_weightlifting", label_vi: "Cử tạ Olympic", label_en: "Olympic Weightlifting" },
      { id: "fitness_model", label_vi: "Commercial Fitness Model" },
    ],
  },
  {
    key: "calisthenic",
    label_vi: "Calisthenic / Trọng lượng cơ thể",
    leaves: [
      { id: "statics", label_vi: "Kỹ thuật giữ tĩnh / Isometric", label_en: "Statics" },
      { id: "dynamics", label_vi: "Kỹ thuật động & nhào lộn", label_en: "Dynamics / Freestyle" },
      { id: "endurance", label_vi: "Sức bền thể trọng", label_en: "Sets & Reps / Endurance" },
      { id: "weighted", label_vi: "Calisthenics mang thêm tạ", label_en: "Weighted Calisthenics" },
    ],
  },
  {
    key: "martial",
    label_vi: "Võ thuật",
    leaves: [
      { id: "vovinam", label_vi: "Vovinam (Việt Võ Đạo)" },
      { id: "vo_co_truyen", label_vi: "Võ Cổ Truyền Việt Nam" },
      { id: "nhat_nam", label_vi: "Nhất Nam" },
      { id: "taekwondo", label_vi: "Taekwondo" },
      { id: "karate", label_vi: "Karate" },
      { id: "judo", label_vi: "Judo (Nhu đạo)" },
      { id: "boxing", label_vi: "Boxing (Quyền Anh)" },
      { id: "muay", label_vi: "Muay Thai & Kickboxing" },
      { id: "bjj", label_vi: "Brazilian Jiu-Jitsu (BJJ)" },
      { id: "mma", label_vi: "MMA (Võ thuật tổng hợp)" },
    ],
  },
  {
    key: "sport",
    label_vi: "Thể thao",
    leaves: [
      { id: "soccer", label_vi: "Bóng Đá" },
      { id: "volleyball", label_vi: "Bóng Chuyền" },
      { id: "basketball", label_vi: "Bóng Rổ" },
      { id: "swimming", label_vi: "Bơi Lội" },
      { id: "badminton", label_vi: "Cầu Lông" },
      { id: "endurance_run", label_vi: "Chạy Bền" },
      { id: "tennis", label_vi: "Tennis" },
      { id: "pickleball", label_vi: "Pickleball" },
    ],
  },
  {
    key: "other",
    label_vi: "Khác",
    leaves: [
      { id: "pilates", label_vi: "Pilates (Mat & Reformer)" },
      { id: "yoga", label_vi: "Yoga" },
      { id: "dance", label_vi: "Dance" },
    ],
  },
  {
    key: "hybrid",
    label_vi: "Hybrid / Kết hợp",
    leaves: [],
  },
];

export const DIRECTION_COMING_SOON =
  "Lộ trình này sắp ra mắt. Chọn một bước nền (màu xanh) để tiếp tục.";

export const DIRECTION_SPECIALIZATION_PENDING =
  "TAPTOT đang trao đổi với chuyên gia để lên giáo trình phù hợp.";

export function isDirectionReady(selection: DirectionSelection): boolean {
  if (selection.kind === "foundation") return true;
  return (
    selection.kind === "challenge" &&
    (selection.offer === "challenge_100" || selection.offer === "fitness_advanced")
  );
}

export function challengesForParent(parent: FamiliarizationPath) {
  return CHALLENGE_BRANCHES.filter((branch) => branch.parent === parent);
}

export function selectionTrunkPath(selection: DirectionSelection): FamiliarizationPath {
  if (selection.kind === "foundation") return selection.path;
  if (selection.kind === "challenge") {
    return (
      CHALLENGE_BRANCHES.find((branch) => branch.key === selection.offer)?.parent ??
      "advanced_foundation"
    );
  }
  return "advanced_foundation";
}

export function directionLabel(selection: DirectionSelection): string {
  if (selection.kind === "foundation") {
    return (
      FOUNDATION_NODES.find((node) => node.key === selection.path)?.label_vi ??
      "Lộ trình nền"
    );
  }
  if (selection.kind === "challenge") {
    return (
      CHALLENGE_BRANCHES.find((branch) => branch.key === selection.offer)?.label_vi ??
      "Thử thách"
    );
  }
  const branch = SPECIALIZATION_BRANCHES.find((item) => item.key === selection.branch);
  if (!branch) return "Chuyên sâu";
  if (!selection.leaf) return branch.label_vi;
  const leaf =
    branch.leaves.find((item) => item.id === selection.leaf)?.label_vi ?? "Sắp ra mắt";
  return `${branch.label_vi} · ${leaf}`;
}

export function selectionFromBuilderState(
  familiarization: boolean,
  path: FamiliarizationPath,
  offer: ChallengeOffer,
): DirectionSelection {
  if (familiarization) return { kind: "foundation", path };
  return { kind: "challenge", offer };
}

export const DEFAULT_DIRECTION_SELECTION: DirectionSelection = {
  kind: "foundation",
  path: "first_push_pull",
};
