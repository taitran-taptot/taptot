"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { myExercisesApi, type MyExercise, type MyExercisePayload } from "@/lib/myExercisesApi";
import type { Label } from "@/lib/types";
import ExerciseThumb from "./ExerciseThumb";
import Modal from "./Modal";

const TYPES = [
  { value: "main", label: "Chính" },
  { value: "warmup", label: "Khởi động" },
  { value: "cooldown", label: "Hồi phục" },
  { value: "cardio", label: "Cardio" },
];

const PAGE_SIZE = 12;

const empty: MyExercisePayload = {
  name_vi: "",
  muscle_group_id: 0,
  exercise_type: "main",
  notes_vi: "",
  video_url: "",
  instruction_vi: "",
};

function ExerciseForm({
  form,
  setForm,
  muscles,
  saving,
  error,
  submitLabel,
  onSubmit,
}: {
  form: MyExercisePayload;
  setForm: (next: MyExercisePayload) => void;
  muscles: Label[];
  saving: boolean;
  error: string;
  submitLabel: string;
  onSubmit: () => void;
}) {
  return (
    <form
      className="space-y-3 p-4"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
    >
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      <label className="block text-sm font-medium text-slate-700">
        Tên bài
        <input
          className="field mt-1"
          value={form.name_vi}
          onChange={(e) => setForm({ ...form, name_vi: e.target.value })}
          required
        />
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Nhóm cơ
        <select
          className="field mt-1"
          value={form.muscle_group_id || ""}
          onChange={(e) => setForm({ ...form, muscle_group_id: Number(e.target.value) })}
          required
        >
          {muscles.map((m) => (
            <option key={m.id} value={m.id}>
              {m.label_vi}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Phần buổi
        <select
          className="field mt-1"
          value={form.exercise_type || "main"}
          onChange={(e) => setForm({ ...form, exercise_type: e.target.value })}
        >
          {TYPES.map((t) => (
            <option key={t.value} value={t.value}>
              {t.label}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Video (URL YouTube hoặc file)
        <input
          className="field mt-1"
          value={form.video_url || ""}
          onChange={(e) => setForm({ ...form, video_url: e.target.value })}
          placeholder="https://www.youtube.com/watch?v=…"
        />
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Cách làm
        <textarea
          className="field mt-1 min-h-[80px]"
          value={form.instruction_vi || ""}
          onChange={(e) => setForm({ ...form, instruction_vi: e.target.value })}
        />
      </label>
      <label className="block text-sm font-medium text-slate-700">
        Ghi chú
        <input
          className="field mt-1"
          value={form.notes_vi || ""}
          onChange={(e) => setForm({ ...form, notes_vi: e.target.value })}
        />
      </label>
      <button type="submit" disabled={saving} className="w-full rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white">
        {saving ? "Đang lưu…" : submitLabel}
      </button>
    </form>
  );
}

export default function HlvExercisesPanel() {
  const [items, setItems] = useState<MyExercise[]>([]);
  const [muscles, setMuscles] = useState<Label[]>([]);
  const [form, setForm] = useState<MyExercisePayload>(empty);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [formErr, setFormErr] = useState("");
  const [mode, setMode] = useState<"add" | "edit" | "delete" | null>(null);
  const [active, setActive] = useState<MyExercise | null>(null);

  const load = useCallback(async (nextPage: number) => {
    setLoading(true);
    setError("");
    try {
      const res = await myExercisesApi.list(nextPage, PAGE_SIZE);
      setItems(res.items);
      setPages(res.pages);
      setPage(res.page);
    } catch (e) {
      setError((e as Error).message || "Không tải được bài tập");
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(1);
    api
      .bodyPartLabels()
      .then((d) => {
        const opts = (d.items || []).filter((x) => x.id && !x.is_filter_only);
        setMuscles(opts);
        setForm((f) => (f.muscle_group_id ? f : { ...f, muscle_group_id: opts[0]?.id || 0 }));
      })
      .catch(() => {});
  }, [load]);

  function openAdd() {
    setForm({ ...empty, muscle_group_id: form.muscle_group_id || muscles[0]?.id || 0 });
    setFormErr("");
    setActive(null);
    setMode("add");
  }

  function openEdit(row: MyExercise) {
    setActive(row);
    setForm({
      name_vi: row.name_vi,
      muscle_group_id: row.muscle_group_id,
      exercise_type: row.exercise_type || "main",
      notes_vi: row.notes_vi || "",
      video_url: row.video_url || "",
      instruction_vi: row.instruction_vi || "",
    });
    setFormErr("");
    setMode("edit");
  }

  function closeModal() {
    setMode(null);
    setActive(null);
    setFormErr("");
  }

  async function save() {
    setSaving(true);
    setFormErr("");
    try {
      const payload: MyExercisePayload = {
        name_vi: form.name_vi.trim(),
        muscle_group_id: form.muscle_group_id,
        exercise_type: form.exercise_type || "main",
        notes_vi: form.notes_vi?.trim() || null,
        video_url: form.video_url?.trim() || null,
        instruction_vi: form.instruction_vi?.trim() || null,
      };
      if (mode === "edit" && active) await myExercisesApi.update(active.id, payload);
      else await myExercisesApi.create(payload);
      closeModal();
      await load(mode === "add" ? 1 : page);
    } catch (err) {
      setFormErr((err as Error).message || "Không lưu được");
    } finally {
      setSaving(false);
    }
  }

  async function confirmDelete() {
    if (!active) return;
    setSaving(true);
    setFormErr("");
    try {
      await myExercisesApi.remove(active.id);
      closeModal();
      const next = items.length === 1 && page > 1 ? page - 1 : page;
      await load(next);
    } catch (err) {
      setFormErr((err as Error).message || "Không xóa được");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-lg font-bold text-slate-900">Bài tập của tôi</h2>
        <button type="button" onClick={openAdd} className="rounded-xl bg-brand-500 px-4 py-2.5 text-sm font-bold text-white">
          Thêm mới
        </button>
      </div>
      {error ? <p className="text-sm text-red-600">{error}</p> : null}
      {loading ? <p className="text-sm text-slate-400">Đang tải…</p> : null}
      <ul className="grid gap-3 sm:grid-cols-2">
        {items.map((row) => (
          <li key={row.id} className="flex gap-3 rounded-2xl bg-white p-3 shadow-soft">
            <ExerciseThumb
              gif={row.gif_url}
              image={row.image_url}
              video={row.video_url}
              bodyPart=""
              className="h-20 w-16 shrink-0 rounded-xl"
              emojiSize="text-2xl"
              alt={row.name_vi}
            />
            <div className="min-w-0 flex-1">
              <p className="font-semibold text-slate-800">{row.name_vi}</p>
              <p className="text-xs text-slate-500">
                {row.muscle_name_vi || ""} · {TYPES.find((t) => t.value === row.exercise_type)?.label || row.exercise_type}
              </p>
              <div className="mt-2 flex gap-2">
                <button type="button" className="text-sm font-semibold text-brand-600" onClick={() => openEdit(row)}>
                  Sửa
                </button>
                <button
                  type="button"
                  className="text-sm font-semibold text-red-600"
                  onClick={() => {
                    setActive(row);
                    setFormErr("");
                    setMode("delete");
                  }}
                >
                  Xóa
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      {!loading && items.length === 0 ? (
        <p className="text-sm text-slate-400">Chưa có bài riêng. Bấm Thêm mới để tạo.</p>
      ) : null}
      {pages > 1 ? (
        <div className="flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40"
            onClick={() => void load(page - 1)}
          >
            Trước
          </button>
          <span className="text-sm text-slate-500">
            Trang {page}/{pages}
          </span>
          <button
            type="button"
            disabled={page >= pages}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-sm disabled:opacity-40"
            onClick={() => void load(page + 1)}
          >
            Sau
          </button>
        </div>
      ) : null}

      <Modal open={mode === "add"} onClose={closeModal} title="Thêm bài tập">
        <ExerciseForm
          form={form}
          setForm={setForm}
          muscles={muscles}
          saving={saving}
          error={formErr}
          submitLabel="Tạo bài"
          onSubmit={() => void save()}
        />
      </Modal>
      <Modal open={mode === "edit"} onClose={closeModal} title={`Sửa: ${active?.name_vi || ""}`}>
        <ExerciseForm
          form={form}
          setForm={setForm}
          muscles={muscles}
          saving={saving}
          error={formErr}
          submitLabel="Lưu"
          onSubmit={() => void save()}
        />
      </Modal>
      <Modal open={mode === "delete"} onClose={closeModal} title="Xóa bài tập">
        <div className="space-y-4 p-4">
          {formErr ? <p className="text-sm text-red-600">{formErr}</p> : null}
          <p className="text-sm text-slate-600">
            Xóa <span className="font-semibold">{active?.name_vi}</span>? Nếu bài đang nằm trong lịch, hệ thống sẽ ẩn khỏi danh sách chứ không gỡ khỏi lịch cũ.
          </p>
          <div className="flex gap-2">
            <button type="button" className="flex-1 rounded-xl border border-slate-200 py-2.5 text-sm font-semibold" onClick={closeModal}>
              Hủy
            </button>
            <button
              type="button"
              disabled={saving}
              className="flex-1 rounded-xl bg-red-600 py-2.5 text-sm font-bold text-white"
              onClick={() => void confirmDelete()}
            >
              {saving ? "Đang xóa…" : "Xóa"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
