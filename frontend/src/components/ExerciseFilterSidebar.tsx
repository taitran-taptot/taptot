"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Label } from "@/lib/types";
import {
  WIZARD_EQUIPMENT_GROUPS,
  publicEquipmentImage,
  wizardEquipmentGroupSelected,
} from "@/lib/equipmentCatalog";
import { mediaUrl } from "@/lib/labels";
import { getMuscleTree, toggleMuscleIds, type MuscleTreeGroup } from "@/lib/muscleGroups";
import {
  SPECIALIZATION_BRANCHES,
  type SpecializationBranchKey,
} from "@/lib/directionTree";

const EXERCISE_SPEC_FILTERS = SPECIALIZATION_BRANCHES.filter((branch) => branch.key !== "hybrid").map(
  (branch) => ({
    key: branch.key,
    label_vi:
      branch.key === "gym"
        ? "Thể hình"
        : branch.key === "calisthenic"
          ? "Trọng lượng cơ thể"
          : branch.label_vi,
  }),
);

export interface ExperienceLevel {
  value: number;
  label: string;
  /** Shorter label for the public exercise filter. */
  filterLabel?: string;
  /** Exercise.difficulty values matched by this experience bucket. */
  difficulties: number[];
}

/** Mức kinh nghiệm chọn trong plan / lọc kho bài (map sang độ khó skill 1–4). */
export const EXPERIENCE_LEVELS: ExperienceLevel[] = [
  {
    value: 1,
    label: "0–1 tháng (Mới bắt đầu vận động)",
    filterLabel: "Mới bắt đầu (0–1 tháng)",
    difficulties: [1, 2],
  },
  {
    value: 2,
    label: "1–6 tháng (Đã có thói quen tập / chơi thể thao)",
    filterLabel: "1–6 tháng",
    difficulties: [2, 3],
  },
  {
    value: 3,
    label: "6–12 tháng (Tập hoặc chơi thể thao đều)",
    filterLabel: "6–12 tháng",
    difficulties: [2, 3, 4],
  },
  {
    value: 4,
    label: "Trên 12 tháng (Lâu năm)",
    filterLabel: "Trên 12 tháng",
    difficulties: [3, 4],
  },
];

function RadioRow({
  checked,
  name,
  onChange,
  children,
}: {
  checked: boolean;
  name: string;
  onChange: () => void;
  children: React.ReactNode;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition select-none hover:bg-slate-50">
      <input
        type="radio"
        name={name}
        checked={checked}
        onChange={onChange}
        className="h-4 w-4 shrink-0 cursor-pointer accent-brand-500"
      />
      <span className={`min-w-0 flex-1 leading-snug ${checked ? "font-semibold text-slate-800" : ""}`}>
        {children}
      </span>
    </label>
  );
}

function CheckRow({
  checked,
  indeterminate,
  onChange,
  children,
  indent,
}: {
  checked: boolean;
  indeterminate?: boolean;
  onChange: () => void;
  children: React.ReactNode;
  indent?: boolean;
}) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (ref.current) ref.current.indeterminate = !!indeterminate;
  }, [indeterminate]);
  return (
    <label
      className={`flex cursor-pointer items-center gap-2.5 rounded-lg py-1.5 text-sm text-slate-600 transition select-none hover:bg-slate-50 ${
        indent ? "px-2 pl-8" : "px-2"
      }`}
    >
      <input
        ref={ref}
        type="checkbox"
        checked={checked}
        onChange={onChange}
        className="h-4 w-4 shrink-0 cursor-pointer accent-brand-500"
      />
      <span className={`min-w-0 flex-1 leading-snug ${checked || indeterminate ? "font-semibold text-slate-800" : ""}`}>
        {children}
      </span>
    </label>
  );
}

function MuscleDropdown({
  group,
  bySlug,
  muscleIds,
  open,
  onToggleOpen,
  onChangeMuscleIds,
}: {
  group: MuscleTreeGroup;
  bySlug: Map<string, Label>;
  muscleIds: number[];
  open: boolean;
  onToggleOpen: () => void;
  onChangeMuscleIds: (ids: number[]) => void;
}) {
  const childIds = group.slugs
    .map((slug) => bySlug.get(slug)?.id)
    .filter((id): id is number => typeof id === "number");
  if (!childIds.length) return null;

  const selectedSlugs = group.slugs.filter((slug) => {
    const id = bySlug.get(slug)?.id;
    return id != null && muscleIds.includes(id);
  });
  const allOn = selectedSlugs.length === childIds.length;
  const someOn = selectedSlugs.length > 0 && !allOn;
  const nestable = group.slugs.length > 1;
  const checkRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (checkRef.current) checkRef.current.indeterminate = someOn;
  }, [someOn]);
  const hint =
    someOn ? selectedSlugs.map((slug) => group.childLabels[slug]).filter(Boolean).join(", ") : "";

  return (
    <div className="px-1">
      <div
        className={`flex items-center rounded-xl border transition ${
          selectedSlugs.length
            ? "border-brand-200 bg-brand-50/70"
            : "border-slate-200 bg-white hover:border-slate-300"
        }`}
      >
        <label className="flex min-w-0 flex-1 cursor-pointer items-center gap-2.5 px-3 py-2 text-sm text-slate-700 select-none">
          <input
            ref={checkRef}
            type="checkbox"
            checked={allOn}
            onChange={() => onChangeMuscleIds(toggleMuscleIds(muscleIds, childIds))}
            className="h-4 w-4 shrink-0 cursor-pointer accent-brand-500"
          />
          <span className="min-w-0 flex-1">
            <span className={`block leading-snug ${allOn || someOn ? "font-semibold text-slate-800" : ""}`}>
              {group.label}
            </span>
            {hint ? (
              <span className="block truncate text-[11px] font-medium text-slate-400">{hint}</span>
            ) : null}
          </span>
        </label>
        {nestable && (
          <button
            type="button"
            aria-expanded={open}
            aria-label={open ? `Ẩn chi tiết ${group.label}` : `Chi tiết ${group.label}`}
            onClick={onToggleOpen}
            className="mr-1 grid h-8 w-8 shrink-0 place-items-center rounded-lg text-slate-400 hover:bg-white/80 hover:text-slate-700"
          >
            <svg
              viewBox="0 0 20 20"
              fill="none"
              className={`h-4 w-4 transition ${open ? "rotate-180" : ""}`}
              aria-hidden
            >
              <path
                d="M5 8l5 5 5-5"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        )}
      </div>
      {open && nestable && (
        <div className="mt-1 mb-1 rounded-xl bg-slate-50 p-1">
          {group.slugs.map((slug) => {
            const row = bySlug.get(slug);
            if (!row?.id) return null;
            return (
              <CheckRow
                key={slug}
                checked={muscleIds.includes(row.id)}
                onChange={() => onChangeMuscleIds(toggleMuscleIds(muscleIds, [row.id!]))}
              >
                {group.childLabels[slug] || row.label_vi}
              </CheckRow>
            );
          })}
        </div>
      )}
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-b border-slate-100 px-3 py-4 last:border-b-0">
      <p className="type-kicker mb-2 px-2 text-slate-400">{title}</p>
      {children}
    </div>
  );
}

interface Props {
  specFilter: SpecializationBranchKey | null;
  onChangeSpecFilter: (key: SpecializationBranchKey | null) => void;

  muscleGroups: Label[];
  muscleIds: number[];
  onChangeMuscleIds: (ids: number[]) => void;
  onResetMuscles: () => void;

  bodyweightOnly: boolean;
  equipSlugs: string[];
  onSelectAllEquipment: () => void;
  onToggleBodyweight: () => void;
  onToggleEquipment: (slug: string) => void;
}

export default function ExerciseFilterSidebar({
  specFilter,
  onChangeSpecFilter,
  muscleGroups,
  muscleIds,
  onChangeMuscleIds,
  onResetMuscles,
  bodyweightOnly,
  equipSlugs,
  onSelectAllEquipment,
  onToggleBodyweight,
  onToggleEquipment,
}: Props) {
  const allEquipment = !bodyweightOnly && equipSlugs.length === 0;
  const bySlug = useMemo(() => new Map(muscleGroups.map((m) => [m.key, m])), [muscleGroups]);
  const muscleTree = getMuscleTree();
  const parentKeys = useMemo(() => new Set(muscleTree.map((g) => g.key)), [muscleTree]);
  const knownSlugs = useMemo(() => new Set(muscleTree.flatMap((g) => g.slugs)), [muscleTree]);
  const extraGroups = muscleGroups.filter(
    (m) =>
      m.id != null &&
      !knownSlugs.has(m.key) &&
      !parentKeys.has(m.key) &&
      !m.is_filter_only,
  );
  const [openKeys, setOpenKeys] = useState<Set<string>>(() => new Set());

  return (
    <aside className="rounded-2xl bg-white shadow-soft lg:self-start">
      <Section title="Chuyên sâu">
        <RadioRow
          name="exercise-spec"
          checked={specFilter === null}
          onChange={() => onChangeSpecFilter(null)}
        >
          Tất cả
        </RadioRow>
        {EXERCISE_SPEC_FILTERS.map((branch) => (
          <RadioRow
            key={branch.key}
            name="exercise-spec"
            checked={specFilter === branch.key}
            onChange={() => onChangeSpecFilter(branch.key)}
          >
            {branch.label_vi}
          </RadioRow>
        ))}
      </Section>

      <Section title="Nhóm cơ">
        <div className="space-y-1.5">
          <CheckRow checked={muscleIds.length === 0} onChange={onResetMuscles}>
            Tất cả nhóm cơ
          </CheckRow>
          {muscleTree.map((group) => (
            <MuscleDropdown
              key={group.key}
              group={group}
              bySlug={bySlug}
              muscleIds={muscleIds}
              open={openKeys.has(group.key)}
              onToggleOpen={() =>
                setOpenKeys((prev) => {
                  const next = new Set(prev);
                  if (next.has(group.key)) next.delete(group.key);
                  else next.add(group.key);
                  return next;
                })
              }
              onChangeMuscleIds={onChangeMuscleIds}
            />
          ))}
          {extraGroups.map((m) => (
            <CheckRow
              key={m.id != null ? `muscle-${m.id}` : `muscle-${m.key}`}
              checked={!!m.id && muscleIds.includes(m.id)}
              onChange={() => m.id && onChangeMuscleIds(toggleMuscleIds(muscleIds, [m.id]))}
            >
              {m.label_vi}
            </CheckRow>
          ))}
        </div>
      </Section>

      <Section title="Dụng cụ">
        <CheckRow checked={allEquipment} onChange={onSelectAllEquipment}>
          Tất cả
        </CheckRow>
        <CheckRow checked={bodyweightOnly} onChange={onToggleBodyweight}>
          Không dụng cụ
        </CheckRow>
        {WIZARD_EQUIPMENT_GROUPS.map((group) => {
          const checked = wizardEquipmentGroupSelected(equipSlugs, group);
          const thumbSlug = group.products?.[0]?.slug || group.slugs[0];
          const src = mediaUrl(publicEquipmentImage(thumbSlug));
          return (
            <label
              key={group.id}
              className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition select-none hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={checked}
                onChange={() => onToggleEquipment(group.id)}
                className="h-4 w-4 shrink-0 cursor-pointer accent-brand-500"
              />
              {src ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={src} alt="" className="h-8 w-8 shrink-0 rounded-md bg-slate-50 object-contain" />
              ) : (
                <span className="h-8 w-8 shrink-0 rounded-md bg-slate-100" aria-hidden />
              )}
              <span className={`min-w-0 flex-1 leading-snug ${checked ? "font-semibold text-slate-800" : ""}`}>
                {group.label_vi}
              </span>
            </label>
          );
        })}
      </Section>
    </aside>
  );
}
