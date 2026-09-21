"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  adminCatalogApi,
  type AdminExercise,
  type AdminExercisePayload,
  type EquipmentRow,
  type MuscleGroupRow,
} from "@/lib/adminCatalogApi";
import { getStoredUser } from "@/lib/auth";
import {
  MOVEMENT_PATTERN_OPTS,
  MOVEMENT_ROLE_OPTS,
  VENUE_OPTS,
  difficultyLabel,
  movementPatternLabel,
  movementRoleLabel,
} from "@/lib/labels";

const emptyForm: AdminExercisePayload = {
  name_vi: "",
  name_en: "",
  muscle_group_id: 0,
  exercise_type: "main",
  movement_role: "compound",
  movement_pattern: "h_push",
  venue: "both",
  difficulty: 2,
  notes_vi: "",
  is_active: true,
};

export default function CatalogExerciseAdmin() {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [items, setItems] = useState<AdminExercise[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [q, setQ] = useState("");
  const [pattern, setPattern] = useState("");
  const [role, setRole] = useState("");
  const [venue, setVenue] = useState("");
  const [difficulty, setDifficulty] = useState<number | "">("");
  const [muscleId, setMuscleId] = useState<number | "">("");
  const [activeFilter, setActiveFilter] = useState("true");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [muscles, setMuscles] = useState<MuscleGroupRow[]>([]);
  const [equipOpts, setEquipOpts] = useState<EquipmentRow[]>([]);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [form, setForm] = useState<AdminExercisePayload>(emptyForm);
  const [equipIds, setEquipIds] = useState<number[]>([]);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const user = getStoredUser();
    if (!user || user.role !== "admin") {
      router.replace("/tai-khoan/ke-hoach");
      return;
    }
    setAllowed(true);
  }, [router]);

  useEffect(() => {
    if (!allowed) return;
    Promise.all([adminCatalogApi.muscleGroups(), adminCatalogApi.equipment()])
      .then(([mg, eq]) => {
        setMuscles(mg.items || []);
        setEquipOpts((eq.items || []).filter((e) => e.is_active !== false));
        setForm((f) =>
          f.muscle_group_id ? f : { ...f, muscle_group_id: mg.items?.[0]?.id || 0 },
        );
      })
      .catch(() => {});
  }, [allowed]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await adminCatalogApi.listExercises({
        page,
        page_size: 20,
        q,
        muscle_group_id: muscleId,
        movement_pattern: pattern,
        movement_role: role,
        venue,
        difficulty,
        is_active: activeFilter,
      });
      setItems(res.items);
      setTotal(res.total);
      setPages(res.pages);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Không tải được danh sách");
    } finally {
      setLoading(false);
    }
  }, [page, q, muscleId, pattern, role, venue, difficulty, activeFilter]);

  useEffect(() => {
    if (allowed) void load();
  }, [allowed, load]);

  function startCreate() {
    setEditingId(null);
    setEquipIds([]);
    setForm({
      ...emptyForm,
      muscle_group_id: muscles[0]?.id || 0,
    });
  }

  async function startEdit(row: AdminExercise) {
    setEditingId(row.id);
    setForm({
      name_vi: row.name_vi,
      name_en: row.name_en || "",
      muscle_group_id: row.muscle_group_id,
      exercise_type: row.exercise_type || "main",
      movement_role: row.movement_role || "compound",
      movement_pattern: row.movement_pattern || "other",
      venue: row.venue || "both",
      difficulty: Number(row.difficulty) || 2,
      notes_vi: row.notes_vi || "",
      is_active: row.is_active,
    });
    try {
      const eq = await adminCatalogApi.getEquipment(row.id);
      setEquipIds(eq.equipment_ids || []);
    } catch {
      setEquipIds([]);
    }
  }

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name_vi.trim() || !form.muscle_group_id) {
      setError("Cần tên tiếng Việt và nhóm cơ.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const body: AdminExercisePayload = {
        ...form,
        name_vi: form.name_vi.trim(),
        name_en: form.name_en?.trim() || null,
        notes_vi: form.notes_vi?.trim() || null,
      };
      let id = editingId;
      if (id == null) {
        const created = await adminCatalogApi.createExercise(body);
        id = created.id;
      } else {
        await adminCatalogApi.updateExercise(id, body);
      }
      await adminCatalogApi.putEquipment(id, equipIds);
      await load();
      setEditingId(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Lưu thất bại");
    } finally {
      setSaving(false);
    }
  }

  function toggleEquip(id: number) {
    setEquipIds((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));
  }

  if (!allowed) {
    return <p className="py-12 text-center text-slate-500">Chỉ tài khoản admin mới vào được trang này.</p>;
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold text-slate-900">Quản trị bài tập</h1>
      <p className="mt-1 text-sm text-slate-500">
        Sửa metadata generator V1.6 (pattern, role, venue, độ khó, dụng cụ). Ẩn bài = tắt active, không xóa cứng.
      </p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <input
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          placeholder="Tìm tên…"
          value={q}
          onChange={(e) => {
            setPage(1);
            setQ(e.target.value);
          }}
        />
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={pattern}
          onChange={(e) => {
            setPage(1);
            setPattern(e.target.value);
          }}
        >
          <option value="">Mọi pattern</option>
          {MOVEMENT_PATTERN_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={role}
          onChange={(e) => {
            setPage(1);
            setRole(e.target.value);
          }}
        >
          <option value="">Mọi role</option>
          {MOVEMENT_ROLE_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={venue}
          onChange={(e) => {
            setPage(1);
            setVenue(e.target.value);
          }}
        >
          <option value="">Mọi venue</option>
          {VENUE_OPTS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={muscleId}
          onChange={(e) => {
            setPage(1);
            setMuscleId(e.target.value ? Number(e.target.value) : "");
          }}
        >
          <option value="">Mọi nhóm cơ</option>
          {muscles.map((m) => (
            <option key={m.id} value={m.id}>
              {m.name_vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={difficulty}
          onChange={(e) => {
            setPage(1);
            setDifficulty(e.target.value ? Number(e.target.value) : "");
          }}
        >
          <option value="">Mọi độ khó</option>
          {[1, 2, 3, 4].map((d) => (
            <option key={d} value={d}>
              {difficultyLabel(d).vi}
            </option>
          ))}
        </select>
        <select
          className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
          value={activeFilter}
          onChange={(e) => {
            setPage(1);
            setActiveFilter(e.target.value);
          }}
        >
          <option value="">Active + ẩn</option>
          <option value="true">Đang hiện</option>
          <option value="false">Đã ẩn</option>
        </select>
        <button
          type="button"
          className="rounded-lg bg-brand-600 px-3 py-2 text-sm font-medium text-white"
          onClick={startCreate}
        >
          Thêm bài
        </button>
      </div>

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

      <div className="mt-6 grid gap-8 lg:grid-cols-2">
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          {loading ? (
            <p className="p-6 text-sm text-slate-400">Đang tải…</p>
          ) : (
            <table className="min-w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Tên</th>
                  <th className="px-3 py-2">Pattern</th>
                  <th className="px-3 py-2">Khó</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr
                    key={row.id}
                    className={`cursor-pointer border-t border-slate-100 hover:bg-brand-50 ${
                      editingId === row.id ? "bg-brand-50" : ""
                    } ${row.is_active ? "" : "opacity-50"}`}
                    onClick={() => void startEdit(row)}
                  >
                    <td className="px-3 py-2 text-slate-400">{row.id}</td>
                    <td className="px-3 py-2">
                      <div className="font-medium text-slate-800">{row.name_vi}</div>
                      <div className="text-xs text-slate-400">
                        {row.muscle_name_vi} · {movementRoleLabel(row.movement_role)?.vi}
                      </div>
                    </td>
                    <td className="px-3 py-2">{movementPatternLabel(row.movement_pattern)?.vi}</td>
                    <td className="px-3 py-2">{difficultyLabel(row.difficulty).vi}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="flex items-center justify-between border-t border-slate-100 px-3 py-2 text-xs text-slate-500">
            <span>
              {total} bài · trang {page}/{pages}
            </span>
            <span className="flex gap-2">
              <button type="button" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Trước
              </button>
              <button type="button" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                Sau
              </button>
            </span>
          </div>
        </div>

        <form onSubmit={(e) => void save(e)} className="space-y-3 rounded-xl border border-slate-200 p-4">
          <h2 className="font-medium text-slate-800">{editingId == null ? "Bài mới" : `Sửa #${editingId}`}</h2>
          <label className="block text-sm">
            Tên VI
            <input
              required
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_vi}
              onChange={(e) => setForm({ ...form, name_vi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Tên EN
            <input
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              value={form.name_en || ""}
              onChange={(e) => setForm({ ...form, name_en: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="block text-sm">
              Nhóm cơ
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.muscle_group_id}
                onChange={(e) => setForm({ ...form, muscle_group_id: Number(e.target.value) })}
              >
                {muscles.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name_vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Loại
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.exercise_type}
                onChange={(e) => setForm({ ...form, exercise_type: e.target.value })}
              >
                <option value="main">Bài chính</option>
                <option value="warmup">Khởi động</option>
                <option value="cooldown">Giãn cơ</option>
                <option value="cardio">Cardio</option>
              </select>
            </label>
            <label className="block text-sm">
              Role
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.movement_role}
                onChange={(e) => setForm({ ...form, movement_role: e.target.value })}
              >
                {MOVEMENT_ROLE_OPTS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Pattern
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.movement_pattern}
                onChange={(e) => setForm({ ...form, movement_pattern: e.target.value })}
              >
                {MOVEMENT_PATTERN_OPTS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Venue
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.venue}
                onChange={(e) => setForm({ ...form, venue: e.target.value })}
              >
                {VENUE_OPTS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.vi}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              Độ khó
              <select
                className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
                value={form.difficulty}
                onChange={(e) => setForm({ ...form, difficulty: Number(e.target.value) })}
              >
                {[1, 2, 3, 4].map((d) => (
                  <option key={d} value={d}>
                    {d} · {difficultyLabel(d).vi}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="block text-sm">
            Ghi chú
            <textarea
              className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2"
              rows={2}
              value={form.notes_vi || ""}
              onChange={(e) => setForm({ ...form, notes_vi: e.target.value })}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_active}
              onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
            />
            Đang hiện (tắt = ẩn khỏi generate)
          </label>
          <fieldset className="max-h-40 overflow-y-auto rounded-lg border border-slate-100 p-2 text-sm">
            <legend className="px-1 text-slate-500">Dụng cụ (trống = không dụng cụ)</legend>
            {equipOpts.map((eq) => (
              <label key={eq.id} className="flex items-center gap-2 py-0.5">
                <input
                  type="checkbox"
                  checked={equipIds.includes(eq.id)}
                  onChange={() => toggleEquip(eq.id)}
                />
                {eq.name_vi}
              </label>
            ))}
          </fieldset>
          <button
            type="submit"
            disabled={saving}
            className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
          >
            {saving ? "Đang lưu…" : "Lưu"}
          </button>
        </form>
      </div>
    </div>
  );
}
