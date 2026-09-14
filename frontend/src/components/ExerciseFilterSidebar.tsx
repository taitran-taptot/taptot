"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { Label } from "@/lib/types";
import {
  PUBLIC_EQUIPMENT_KEYS,
  PUBLIC_EQUIPMENT_LABELS,
  publicEquipmentImage,
} from "@/lib/equipmentCatalog";
import { mediaUrl } from "@/lib/labels";
import { getMuscleTree, toggleMuscleIds, type MuscleTreeGroup } from "@/lib/muscleGroups";

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

export const EQUIPMENT_FILTERS: { key: string; label: string }[] = PUBLIC_EQUIPMENT_KEYS.map((key) => ({
  key,
  label: PUBLIC_EQUIPMENT_LABELS[key],
}));

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
      <p className="mb-2 px-2 text-xs font-bold tracking-wide text-slate-400 uppercase">{title}</p>
      {children}
    </div>
  );
}

interface Props {
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
        {EQUIPMENT_FILTERS.map((eq) => {
          const src = mediaUrl(publicEquipmentImage(eq.key));
          return (
            <label
              key={eq.key}
              className="flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm text-slate-600 transition select-none hover:bg-slate-50"
            >
              <input
                type="checkbox"
                checked={equipSlugs.includes(eq.key)}
                onChange={() => onToggleEquipment(eq.key)}
                className="h-4 w-4 shrink-0 cursor-pointer accent-brand-500"
              />
              {src ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={src} alt="" className="h-8 w-8 shrink-0 rounded-md bg-slate-50 object-contain" />
              ) : (
                <span className="h-8 w-8 shrink-0 rounded-md bg-slate-100" aria-hidden />
              )}
              <span className={`min-w-0 flex-1 leading-snug ${equipSlugs.includes(eq.key) ? "font-semibold text-slate-800" : ""}`}>
                {eq.label}
              </span>
            </label>
          );
        })}
      </Section>
    </aside>
  );
}
