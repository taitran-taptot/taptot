"use client";

import { useEffect, useState } from "react";
import Modal from "./Modal";
import ExerciseThumb from "./ExerciseThumb";
import { api } from "@/lib/api";
import { gifUrl, mediaUrl } from "@/lib/labels";
import { isDirectVideoUrl, youtubeEmbedUrl } from "@/lib/sharePlan";
import type { ExerciseListItem } from "@/lib/types";

export type FitnessPreset = { label: string; value: string };

export type FitnessTestValues = {
  pushups: string;
  pullups: string;
  plankSeconds: string;
  squats: string;
};

type TestKey = keyof FitnessTestValues;

const TESTS: {
  key: TestKey;
  title: string;
  query: string;
  preferNames: string[];
  rejectNames?: string[];
  unit: string;
  inputLabel: string;
  preferBodyweight?: boolean;
}[] = [
  {
    key: "pushups",
    title: "Chống đẩy",
    query: "chống đẩy",
    preferNames: ["push up", "push-up", "pushups", "chong day"],
    rejectNames: ["knee", "diamond", "decline", "incline", "clap", "burpee"],
    unit: "cái",
    inputLabel: "Số cái tối đa",
    preferBodyweight: true,
  },
  {
    key: "pullups",
    title: "Pull-up",
    query: "pull up",
    preferNames: ["pull ups", "pull-up", "pull up", "hit xa"],
    rejectNames: ["assisted", "weighted", "machine", "band", "wide", "neutral", "chin", "dip"],
    unit: "cái",
    inputLabel: "Số cái tối đa",
  },
  {
    key: "plankSeconds",
    title: "Plank",
    query: "front plank",
    preferNames: ["front plank on elbows", "chong nguoi chong khuyu", "front plank"],
    rejectNames: ["hand plank", "side", "thang tay", "straight", "mountain", "nghieng"],
    unit: "giây",
    inputLabel: "Số giây giữ được",
    preferBodyweight: true,
  },
  {
    key: "squats",
    title: "Squat",
    query: "bodyweight squat",
    preferNames: ["bodyweight squat", "ngoi xom khong ta"],
    rejectNames: [
      "split",
      "bulgarian",
      "jump",
      "sumo",
      "goblet",
      "hack",
      "smith",
      "pause",
      "box",
      "cossack",
      "belt",
      "isometric",
      "hold",
      "wall sit",
      "tuong",
      "truoc-sau",
      "truoc sau",
    ],
    unit: "cái",
    inputLabel: "Số cái tối đa",
    preferBodyweight: true,
  },
];

function foldVi(text: string): string {
  return text
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function isBodyweight(ex: ExerciseListItem): boolean {
  const slugs = (ex.equipment_slugs || []).map((s) => s.toLowerCase());
  if (slugs.length === 0) return true;
  const blob = `${ex.equipment || ""} ${slugs.join(" ")}`.toLowerCase();
  return (
    /khong dung cu|bodyweight|no.?equip|none|—|-/.test(blob) ||
    slugs.every((s) => s === "bodyweight" || s === "none")
  );
}

function pickExercise(
  items: ExerciseListItem[],
  preferNames: string[],
  rejectNames: string[] | undefined,
  preferBodyweight: boolean,
): ExerciseListItem | null {
  if (!items.length) return null;
  let best = items[0];
  let bestScore = -Infinity;
  for (const ex of items) {
    const blob = foldVi(`${ex.name_vi} ${ex.name_en}`);
    let score = 0;
    for (const name of preferNames) {
      const n = foldVi(name);
      if (blob === n) score += 100;
      else if (blob.includes(n)) score += 40;
    }
    for (const bad of rejectNames || []) {
      if (blob.includes(foldVi(bad))) score -= 80;
    }
    if (preferBodyweight) score += isBodyweight(ex) ? 25 : -30;
    if (ex.is_beginner_friendly) score += 2;
    if (ex.video_url || ex.gif_url) score += 3;
    // Prefer shorter classic names (e.g. "Pull Ups", "Bodyweight Squat").
    score -= Math.min(blob.length, 40) * 0.2;
    if (score > bestScore) {
      bestScore = score;
      best = ex;
    }
  }
  return best;
}

function TestMedia({ ex, title }: { ex: ExerciseListItem | null; title: string }) {
  const [playYt, setPlayYt] = useState(false);
  const yt = youtubeEmbedUrl(ex?.video_url);
  const direct =
    (isDirectVideoUrl(ex?.video_url) ? mediaUrl(ex?.video_url) : null) ||
    (isDirectVideoUrl(ex?.gif_url) ? gifUrl(ex?.gif_url) || mediaUrl(ex?.gif_url) : null);

  useEffect(() => {
    setPlayYt(false);
  }, [ex?.id]);

  if (yt && playYt) {
    return (
      <div className="aspect-video w-full overflow-hidden rounded-xl bg-black">
        <iframe
          title={title}
          src={`${yt}${yt.includes("?") ? "&" : "?"}autoplay=1`}
          className="h-full w-full"
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
        />
      </div>
    );
  }

  if (direct) {
    return (
      <video
        src={direct}
        muted
        playsInline
        loop
        autoPlay
        controls
        className="aspect-video w-full rounded-xl bg-black object-contain"
      />
    );
  }

  return (
    <div className="relative overflow-hidden rounded-xl">
      <ExerciseThumb
        gif={ex?.gif_url}
        image={ex?.image_url}
        video={ex?.video_url}
        bodyPart={ex?.body_part || ""}
        className="aspect-video w-full"
        emojiSize="text-5xl"
        alt={title}
      />
      {yt ? (
        <button
          type="button"
          onClick={() => setPlayYt(true)}
          className="absolute inset-0 grid place-items-center bg-slate-900/25"
          aria-label={`Xem video ${title}`}
        >
          <span className="grid h-12 w-12 place-items-center rounded-full bg-white text-lg font-extrabold text-brand-600 shadow">
            ▶
          </span>
        </button>
      ) : null}
    </div>
  );
}

export default function FitnessTestModal({
  open,
  onClose,
  values,
  onSave,
  presets,
  tone = "default",
}: {
  open: boolean;
  onClose: () => void;
  values: FitnessTestValues;
  onSave: (next: FitnessTestValues) => void;
  presets: Record<TestKey, readonly FitnessPreset[]>;
  tone?: "default" | "beginner";
}) {
  const beginner = tone === "beginner";
  const [draft, setDraft] = useState<FitnessTestValues>(values);
  const [exercises, setExercises] = useState<Partial<Record<TestKey, ExerciseListItem | null>>>({});
  const [loadingMedia, setLoadingMedia] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDraft(values);
  }, [open, values]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoadingMedia(true);
    (async () => {
      const next: Partial<Record<TestKey, ExerciseListItem | null>> = {};
      await Promise.all(
        TESTS.map(async (test) => {
          try {
            const data = await api.searchExercises({ q: test.query, page: 1, page_size: 12 });
            next[test.key] = pickExercise(
              data.items || [],
              test.preferNames,
              test.rejectNames,
              !!test.preferBodyweight,
            );
          } catch {
            next[test.key] = null;
          }
        }),
      );
      if (!cancelled) {
        setExercises(next);
        setLoadingMedia(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  function setField(key: TestKey, value: string) {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }

  function confirm() {
    onSave(draft);
    onClose();
  }

  const title = beginner ? "Ước lượng sức hiện tại" : "Kiểm tra thể lực";
  const subtitle = beginner
    ? "Chưa làm được cũng chọn 0. Không cần cố hết sức — chỉ để lịch khớp với bạn."
    : "Làm tối đa mỗi bài (hoặc để trống nếu chưa thử), rồi xác nhận.";

  return (
    <Modal open={open} onClose={onClose} size="lg" lockScroll title={title}>
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 880px)" }}>
        <div className="shrink-0 border-b border-slate-100 px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-bold sm:text-lg">{title}</h3>
              <p className="mt-1 text-xs text-slate-400">{subtitle}</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-slate-100 text-xl leading-none text-slate-600 hover:bg-slate-200"
              aria-label="Đóng"
            >
              ×
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto overscroll-contain px-4 py-4">
          {TESTS.map((test) => {
            const ex = exercises[test.key] ?? null;
            const inputLabel = beginner ? "Bạn làm được khoảng bao nhiêu?" : test.inputLabel;
            return (
              <div key={test.key} className="rounded-2xl border border-slate-100 bg-slate-50/60 p-3">
                <p className="mb-2 text-sm font-extrabold text-slate-900">{test.title}</p>
                {beginner && test.key === "pullups" ? (
                  <p className="mb-2 text-xs text-slate-500">0 là bình thường nếu mới bắt đầu.</p>
                ) : null}
                {loadingMedia && !ex ? (
                  <div className="grid aspect-video place-items-center rounded-xl bg-slate-100 text-sm text-slate-400">
                    Đang tải video…
                  </div>
                ) : (
                  <TestMedia ex={ex} title={test.title} />
                )}
                {ex?.name_vi && ex.name_vi !== test.title ? (
                  <p className="mt-1.5 text-xs text-slate-400">{ex.name_vi}</p>
                ) : null}
                <label className="mt-3 mb-1.5 block text-sm font-semibold text-slate-600">
                  {inputLabel}
                  {!beginner ? null : (
                    <span className="ml-1 font-normal text-slate-400">({test.unit})</span>
                  )}
                </label>
                <input
                  className="field bg-white"
                  type="number"
                  min={0}
                  inputMode="numeric"
                  placeholder={beginner ? "0 cũng được" : `Ví dụ số ${test.unit}`}
                  value={draft[test.key]}
                  onChange={(e) => setField(test.key, e.target.value)}
                />
                <div className="mt-2 flex flex-wrap gap-2">
                  {presets[test.key].map((p) => (
                    <button
                      key={p.label}
                      type="button"
                      onClick={() => setField(test.key, p.value)}
                      className={`chip ${draft[test.key] === p.value ? "chip-active" : ""}`}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex shrink-0 gap-2 border-t border-slate-100 px-4 py-3">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-bold text-slate-600 hover:bg-slate-50"
          >
            Huỷ
          </button>
          <button
            type="button"
            onClick={confirm}
            className="flex-1 rounded-xl bg-brand-500 py-2.5 text-sm font-bold text-white hover:bg-brand-600"
          >
            Xác nhận
          </button>
        </div>
      </div>
    </Modal>
  );
}
