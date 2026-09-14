"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type ExerciseAlternativesQuery } from "@/lib/api";
import { difficultyLabel } from "@/lib/labels";
import type { ExerciseListItem } from "@/lib/types";
import type { SwapExerciseContext, ExerciseAltContext } from "@/lib/planSwap";
import ExerciseThumb from "./ExerciseThumb";
import Modal from "./Modal";

export default function ExerciseAlternativesModal({
  open,
  exercise,
  canSave,
  loginNext,
  onClose,
  onSelect,
  context,
}: {
  open: boolean;
  exercise: SwapExerciseContext | null;
  canSave: boolean;
  /** Path for guest login CTA, e.g. `/dang-nhap?next=...` */
  loginNext: string;
  onClose: () => void;
  onSelect: (alt: ExerciseListItem) => void | Promise<void>;
  context?: ExerciseAltContext;
}) {
  const [alts, setAlts] = useState<ExerciseListItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [pickingId, setPickingId] = useState<number | null>(null);

  useEffect(() => {
    if (!open || !exercise) {
      setAlts([]);
      setErr("");
      return;
    }
    let cancelled = false;
    setLoading(true);
    setErr("");
    const query: ExerciseAlternativesQuery = {
      location: context?.location,
      no_equipment: context?.no_equipment,
      equipment: context?.equipment_list,
    };
    api
      .exerciseAlternatives(exercise.exercise_id, 8, query)
      .then((items) => {
        if (!cancelled) setAlts(items);
      })
      .catch((e) => {
        if (!cancelled) setErr((e as Error).message || "Không tải được bài thay thế.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [open, exercise?.exercise_id, context?.location, context?.no_equipment, context?.equipment_list?.join(",")]);

  async function pick(alt: ExerciseListItem) {
    if (!canSave || pickingId != null) return;
    setPickingId(alt.id);
    try {
      await onSelect(alt);
      onClose();
    } catch (e) {
      setErr((e as Error).message || "Không lưu được thay đổi.");
    } finally {
      setPickingId(null);
    }
  }

  if (!exercise) return null;

  return (
    <Modal open={open} onClose={onClose} size="lg" lockScroll>
      <div className="flex max-h-[92vh] flex-col">
        <div className="shrink-0 border-b border-slate-100 px-4 py-4 sm:px-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-slate-900">Bài thay thế</h2>
              <p className="mt-0.5 text-sm text-slate-500 [overflow-wrap:anywhere]">
                Thay cho: <span className="font-medium text-slate-700">{exercise.name_vi}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="chip-secondary min-h-[44px] shrink-0 px-3 text-sm font-semibold"
            >
              Đóng
            </button>
          </div>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3 sm:px-5">
          {loading && (
            <p className="py-8 text-center text-sm text-slate-400">Đang tìm bài tương tự…</p>
          )}
          {err && !loading && (
            <p className="rounded-xl bg-rose-50 px-3 py-2.5 text-sm text-rose-700">{err}</p>
          )}
          {!loading && !err && alts.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-400">
              Không có bài thay thế cùng nhóm cơ và phù hợp nơi tập.
            </p>
          )}
          {!loading && alts.length > 0 && (
            <ul className="space-y-2">
              {alts.map((alt) => {
                const diff = difficultyLabel(alt.difficulty_label || alt.difficulty);
                const muscle = alt.body_part || alt.muscle_group || "";
                const busy = pickingId === alt.id;
                return (
                  <li
                    key={alt.id}
                    className="flex items-center gap-3 rounded-xl bg-slate-50 p-2.5 ring-1 ring-slate-100"
                  >
                    <ExerciseThumb
                      gif={alt.gif_url}
                      bodyPart={muscle}
                      className="h-12 w-12 shrink-0 rounded-lg"
                      emojiSize="text-xl"
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-semibold leading-snug text-slate-900 [overflow-wrap:anywhere]">
                        {alt.name_vi}
                      </p>
                      <div className="mt-1 flex flex-wrap items-center gap-1.5">
                        {muscle && (
                          <span className="rounded-full bg-white px-2 py-0.5 text-[11px] font-medium text-slate-500 ring-1 ring-slate-200">
                            {muscle}
                          </span>
                        )}
                        <span className={`badge text-[11px] ${diff.cls}`}>
                          {alt.difficulty_label || diff.vi}
                        </span>
                      </div>
                    </div>
                    {canSave ? (
                      <button
                        type="button"
                        disabled={busy || pickingId != null}
                        onClick={() => void pick(alt)}
                        className="chip-primary min-h-[44px] shrink-0 whitespace-nowrap px-3 text-xs font-bold disabled:opacity-60"
                      >
                        {busy ? "Đang lưu…" : "Chọn bài này"}
                      </button>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        {!canSave && (
          <div className="shrink-0 border-t border-slate-100 px-4 py-3 sm:px-5">
            <Link
              href={loginNext}
              className="flex min-h-[44px] w-full items-center justify-center rounded-xl bg-brand-500 px-4 text-sm font-bold text-white hover:bg-brand-600"
            >
              Đăng nhập để thay bài
            </Link>
          </div>
        )}
      </div>
    </Modal>
  );
}
