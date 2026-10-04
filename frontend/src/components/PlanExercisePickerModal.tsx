"use client";

import { useEffect, useState } from "react";
import Modal from "./Modal";
import ExerciseThumb from "./ExerciseThumb";
import { api } from "@/lib/api";
import type { ExerciseDetail, ExerciseListItem, Label } from "@/lib/types";

export default function PlanExercisePickerModal({
  open,
  onClose,
  excludeIds,
  onPick,
  exerciseType,
  sectionLabel,
}: {
  open: boolean;
  onClose: () => void;
  excludeIds: Set<number>;
  onPick: (ex: ExerciseListItem) => void;
  exerciseType?: string;
  sectionLabel?: string;
}) {
  const [q, setQ] = useState("");
  const [bodyPart, setBodyPart] = useState("");
  const [bodyOpts, setBodyOpts] = useState<Label[]>([]);
  const [items, setItems] = useState<ExerciseListItem[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);
  const [previewId, setPreviewId] = useState<number | null>(null);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setBodyPart("");
    setPage(1);
    setPreviewId(null);
    api
      .bodyPartLabels()
      .then((d) => setBodyOpts(d.items || []))
      .catch(() => setBodyOpts([]));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      setLoading(true);
      api
        .searchExercises({
          q: q || undefined,
          body_part: bodyPart || undefined,
          exercise_type: exerciseType || undefined,
          page: 1,
          page_size: 18,
        })
        .then((d) => {
          setItems(d.items);
          setPages(d.pages);
          setPage(1);
        })
        .catch(() => {
          setItems([]);
          setPages(1);
        })
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(t);
  }, [q, bodyPart, open, exerciseType]);

  async function loadMore() {
    const next = page + 1;
    setLoading(true);
    try {
      const d = await api.searchExercises({
        q: q || undefined,
        body_part: bodyPart || undefined,
        exercise_type: exerciseType || undefined,
        page: next,
        page_size: 18,
      });
      setItems((prev) => [...prev, ...d.items]);
      setPages(d.pages);
      setPage(next);
    } catch {
      /* keep current list */
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Modal open={open} onClose={onClose} size="wide" lockScroll title="Thêm bài tập">
        <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 800px)" }}>
          <div className="shrink-0 border-b border-slate-100 px-4 pb-3 pt-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-base font-bold sm:text-lg">
                  {sectionLabel ? `Thêm bài · ${sectionLabel}` : "Kho bài tập"}
                </h3>
                <p className="mt-1 text-xs text-slate-400">
                  {sectionLabel ? `Bấm thẻ để thêm vào ${sectionLabel.toLowerCase()}.` : "Bấm thẻ để thêm vào phần đang chọn."}
                </p>
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
            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                type="search"
                placeholder="Tìm bài… (vd: squat, ngực, plank)"
                className="field flex-1"
              />
              <select
                value={bodyPart}
                onChange={(e) => setBodyPart(e.target.value)}
                className="field sm:w-44"
                aria-label="Lọc nhóm cơ"
              >
                <option value="">Mọi nhóm cơ</option>
                {bodyOpts.map((opt) => (
                  <option key={opt.key} value={opt.key}>
                    {opt.label_vi}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {items.map((ex) => {
                const disabled = excludeIds.has(ex.id);
                return (
                  <div key={ex.id} className="relative">
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => onPick(ex)}
                      className="w-full overflow-hidden rounded-2xl bg-white text-left shadow-soft ring-1 ring-slate-100 transition hover:-translate-y-0.5 hover:ring-brand-200 disabled:opacity-40"
                    >
                      <ExerciseThumb
                        gif={ex.gif_url}
                        image={ex.image_url}
                        video={ex.video_url}
                        bodyPart={ex.body_part}
                        className="h-28 w-full"
                        emojiSize="text-4xl"
                        alt={ex.name_vi}
                      />
                      <div className="p-2.5">
                        <p className="line-clamp-2 text-sm font-bold leading-snug text-slate-800">{ex.name_vi}</p>
                        <p className="mt-1 text-[11px] font-semibold text-brand-600">
                          {disabled ? "Đã có" : "+ Thêm"}
                        </p>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setPreviewId(ex.id);
                      }}
                      className="absolute right-2 top-2 rounded-full bg-white/90 px-2 py-0.5 text-[11px] font-bold text-slate-600 shadow"
                    >
                      Xem
                    </button>
                  </div>
                );
              })}
            </div>
            {loading && <p className="py-6 text-center text-sm text-slate-400">Đang tải…</p>}
            {!loading && items.length === 0 && (
              <p className="py-8 text-center text-sm text-slate-400">Không thấy bài phù hợp.</p>
            )}
            {!loading && page < pages && (
              <div className="mt-4 text-center">
                <button
                  type="button"
                  onClick={() => void loadMore()}
                  className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-400"
                >
                  Xem thêm
                </button>
              </div>
            )}
          </div>
        </div>
      </Modal>
      <ExerciseQuickPreview id={previewId} onClose={() => setPreviewId(null)} />
    </>
  );
}

function ExerciseQuickPreview({ id, onClose }: { id: number | null; onClose: () => void }) {
  const [data, setData] = useState<ExerciseDetail | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!id) {
      setData(null);
      return;
    }
    setLoading(true);
    api
      .getExercise(id)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [id]);

  const steps =
    data && Array.isArray(data.instruction_steps_vi) && data.instruction_steps_vi.length
      ? data.instruction_steps_vi
      : data?.instruction_vi
        ? [data.instruction_vi]
        : [];

  return (
    <Modal open={!!id} onClose={onClose} size="lg" title={data?.name_vi || "Bài tập"}>
      {loading && <p className="p-6 text-center text-sm text-slate-400">Đang tải…</p>}
      {data && (
        <div>
          <ExerciseThumb
            gif={data.gif_url}
            image={data.image_url}
            video={data.video_url}
            bodyPart={data.body_part}
            className="h-48 w-full"
            emojiSize="text-6xl"
            alt={data.name_vi}
          />
          <div className="space-y-2 p-4">
            <h3 className="text-lg font-bold">{data.name_vi}</h3>
            {steps.length > 0 && (
              <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-600">
                {steps.slice(0, 6).map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            )}
            <button
              type="button"
              onClick={onClose}
              className="mt-2 w-full rounded-xl border border-slate-200 py-2 text-sm font-semibold text-slate-600"
            >
              Đóng
            </button>
          </div>
        </div>
      )}
    </Modal>
  );
}
