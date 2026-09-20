"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { PAGE_SIZE } from "@/lib/config";
import {
  PUBLIC_EQUIPMENT_LABELS,
  isPublicEquipmentKey,
  normalizePublicEquipmentSlug,
} from "@/lib/equipmentCatalog";
import {
  muscleDisplayLabel,
  muscleTreeFromApi,
  rebuildMuscleTreeMaps,
  setMuscleTree,
} from "@/lib/muscleGroups";
import {
  mediaUrl,
  movementPatternLabel,
  movementRoleLabel,
  VENUE_LABEL,
} from "@/lib/labels";
import type { ExerciseDetail, ExerciseListItem, Label } from "@/lib/types";
import { isDirectVideoUrl, youtubeEmbedUrl } from "@/lib/sharePlan";
import { splitCoachLines } from "@/lib/exerciseCopy";
import ExerciseFilterSidebar from "./ExerciseFilterSidebar";
import ExerciseThumb from "./ExerciseThumb";
import Modal from "./Modal";

const toggle = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter((x) => x !== value) : [...list, value];

export default function ExerciseLibrary() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const initialEquip = searchParams.get("equipment") || "";

  const [q, setQ] = useState("");
  const [muscleIds, setMuscleIds] = useState<number[]>([]);
  const [bodyweightOnly, setBodyweightOnly] = useState(false);
  const [equipSlugs, setEquipSlugs] = useState<string[]>(() =>
    initialEquip
      ? normalizePublicEquipmentSlug(initialEquip).filter(isPublicEquipmentKey)
      : [],
  );
  const loadRequestId = useRef(0);

  const [items, setItems] = useState<ExerciseListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [bodyMap, setBodyMap] = useState<Record<string, string>>({});
  const [bodyOpts, setBodyOpts] = useState<Label[]>([]);

  const [selected, setSelected] = useState<number | null>(null);
  const [filtersOpen, setFiltersOpen] = useState(() => !!initialEquip);

  useEffect(() => {
    Promise.all([api.bodyPartLabels(), api.muscleGroupTree()])
      .then(([bp, tree]) => {
        setBodyOpts(bp.items.filter((x) => !x.is_filter_only));
        setBodyMap(Object.fromEntries(bp.items.map((x) => [x.key, x.label_vi])));
        const built = muscleTreeFromApi(tree);
        setMuscleTree(built);
        rebuildMuscleTreeMaps(built);
      })
      .catch(() => {
        api
          .bodyPartLabels()
          .then((bp) => {
            setBodyOpts(bp.items.filter((x) => !x.is_filter_only));
            setBodyMap(Object.fromEntries(bp.items.map((x) => [x.key, x.label_vi])));
          })
          .catch(() => {});
      });
  }, []);

  useEffect(() => {
    const eq = (searchParams.get("equipment") || "").trim();
    if (!eq) return;
    const next = normalizePublicEquipmentSlug(eq).filter(isPublicEquipmentKey);
    if (!next.length) return;
    setEquipSlugs((prev) =>
      prev.length === next.length && prev.every((k, i) => k === next[i]) ? prev : next,
    );
    setBodyweightOnly(false);
    setFiltersOpen(true);
  }, [searchParams]);

  function syncEquipmentQuery(slugs: string[]) {
    const params = new URLSearchParams(searchParams.toString());
    if (slugs.length === 1) params.set("equipment", slugs[0]);
    else params.delete("equipment");
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }

  function selectAllEquipment() {
    setBodyweightOnly(false);
    setEquipSlugs([]);
    syncEquipmentQuery([]);
  }

  function toggleBodyweight() {
    setBodyweightOnly((prev) => {
      const next = !prev;
      if (next) {
        setEquipSlugs([]);
        syncEquipmentQuery([]);
      }
      return next;
    });
  }

  function toggleEquipment(slug: string) {
    setBodyweightOnly(false);
    setEquipSlugs((prev) => {
      const next = toggle(prev, slug);
      syncEquipmentQuery(next);
      return next;
    });
  }

  const activeFilters = muscleIds.length + (bodyweightOnly ? 1 : 0) + equipSlugs.length;

  const clearAll = () => {
    setMuscleIds([]);
    setBodyweightOnly(false);
    setEquipSlugs([]);
    syncEquipmentQuery([]);
  };

  const load = useCallback(
    async (nextPage: number, append: boolean) => {
      setLoading(true);
      setError("");
      const requestId = ++loadRequestId.current;
      try {
        const data = await api.searchExercises({
          q,
          muscle_group_ids: muscleIds.join(","),
          equipment: bodyweightOnly ? undefined : equipSlugs.join(","),
          equipment_categories: bodyweightOnly ? "Không dụng cụ" : undefined,
          page: nextPage,
          page_size: PAGE_SIZE,
        });
        if (requestId !== loadRequestId.current) return;
        const rows = data.items || [];
        setTotal(data.total ?? rows.length);
        setPages(data.pages ?? 1);
        setItems((prev) => {
          const next = append ? [...prev, ...rows] : rows;
          const seen = new Set<number>();
          return next.filter((ex) => {
            if (seen.has(ex.id)) return false;
            seen.add(ex.id);
            return true;
          });
        });
      } catch (e) {
        if (requestId !== loadRequestId.current) return;
        setError((e as Error).message);
      } finally {
        if (requestId === loadRequestId.current) setLoading(false);
      }
    },
    [q, muscleIds, bodyweightOnly, equipSlugs],
  );

  // reload on filter change (debounced for q)
  const first = useRef(true);
  useEffect(() => {
    const t = setTimeout(
      () => {
        setPage(1);
        load(1, false);
      },
      first.current ? 0 : 300,
    );
    first.current = false;
    return () => clearTimeout(t);
  }, [load]);

  return (
    <section>
      <div className="mb-5">
        <h1 className="text-2xl font-extrabold tracking-tight">Kho bài tập</h1>
        <p className="mt-1 text-sm text-slate-500">
          Mặc định hiện toàn bộ bài. Lọc theo nhóm cơ hoặc dụng cụ.
        </p>
      </div>

      <div className="mb-3 lg:hidden">
        <button
          type="button"
          onClick={() => setFiltersOpen((v) => !v)}
          className="rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 shadow-soft"
        >
          {filtersOpen ? "Ẩn bộ lọc" : "Bộ lọc"}
          {activeFilters > 0 ? ` (${activeFilters})` : ""}
        </button>
      </div>

      <div className="grid grid-cols-1 items-start gap-5 lg:grid-cols-[264px_1fr]">
        <div className={filtersOpen ? "block" : "hidden lg:block"}>
          <ExerciseFilterSidebar
            muscleGroups={bodyOpts}
            muscleIds={muscleIds}
            onChangeMuscleIds={setMuscleIds}
            onResetMuscles={() => setMuscleIds([])}
            bodyweightOnly={bodyweightOnly}
            equipSlugs={equipSlugs}
            onSelectAllEquipment={selectAllEquipment}
            onToggleBodyweight={toggleBodyweight}
            onToggleEquipment={toggleEquipment}
          />
        </div>

        <div>
          <div className="mb-4 rounded-2xl bg-white p-4 shadow-soft">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <div className="relative min-w-0 flex-1">
                <svg
                  className="absolute top-1/2 left-3 h-5 w-5 -translate-y-1/2 text-slate-400"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <circle cx="11" cy="11" r="7" />
                  <path d="m21 21-3.5-3.5" />
                </svg>
                <label className="sr-only" htmlFor="exercise-search">
                  Tìm bài tập
                </label>
                <input
                  id="exercise-search"
                  value={q}
                  onChange={(e) => setQ(e.target.value)}
                  type="search"
                  placeholder="Tìm bài tập… (vd: chống đẩy, ngực, squat)"
                  className="field pl-10"
                />
              </div>
            </div>
            {equipSlugs.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-sm text-slate-600">
                <span>
                  Đang xem bài tập với{" "}
                  <b className="text-brand-700">
                    {equipSlugs
                      .map((s) =>
                        isPublicEquipmentKey(s)
                          ? PUBLIC_EQUIPMENT_LABELS[s as keyof typeof PUBLIC_EQUIPMENT_LABELS]
                          : s,
                      )
                      .join(", ")}
                  </b>
                </span>
                <button
                  type="button"
                  onClick={selectAllEquipment}
                  className="font-semibold text-brand-600 hover:underline"
                >
                  Xóa lọc dụng cụ
                </button>
              </div>
            )}
          </div>

          <div className="mb-3 flex items-center gap-3">
            <p className="text-sm text-slate-400">
              {total.toLocaleString("vi-VN")} bài tập phù hợp
            </p>
            {activeFilters > 0 && (
              <button
                onClick={clearAll}
                className="text-sm font-semibold text-brand-600 hover:underline"
              >
                Xóa bộ lọc ({activeFilters})
              </button>
            )}
          </div>

          {error && <div className="py-12 text-center text-rose-500">Lỗi tải dữ liệu: {error}</div>}

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {items.map((ex) => (
                <button
                  key={`exercise-${ex.id}`}
                  onClick={() => setSelected(ex.id)}
                  className="animate-in overflow-hidden rounded-2xl bg-white text-left shadow-soft transition hover:-translate-y-0.5 hover:shadow-lg"
                >
                  <ExerciseThumb
                    gif={ex.gif_url}
                    image={ex.image_url}
                    video={ex.video_url}
                    bodyPart={ex.body_part}
                    eager
                  />
                  <div className="p-4">
                    <p className="clamp-2 leading-snug font-bold">{ex.name_vi}</p>
                    {ex.name_en && ex.name_en !== ex.name_vi && (
                      <p className="mt-0.5 truncate text-xs text-slate-400">{ex.name_en}</p>
                    )}
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {ex.is_beginner_friendly && (
                        <span className="badge badge-new">Phù hợp người mới</span>
                      )}
                      <span className="badge badge-gray">
                        {muscleDisplayLabel(
                          ex.body_part,
                          bodyMap[ex.body_part] || (ex.muscle_group || "").split(" - ")[0] || ex.body_part,
                        )}
                      </span>
                    </div>
                    <p className="mt-2 text-xs text-slate-400">
                      Dụng cụ:{" "}
                      {ex.equipment && ex.equipment !== "—" ? ex.equipment : "Không cần dụng cụ"}
                    </p>
                  </div>
                </button>
            ))}
          </div>

          {loading && (
            <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {Array.from({ length: items.length ? 3 : 6 }).map((_, i) => (
                <div key={i} className="animate-pulse overflow-hidden rounded-2xl bg-white shadow-soft">
                  <div className="h-40 bg-slate-100" />
                  <div className="space-y-2 p-4">
                    <div className="h-4 w-3/4 rounded bg-slate-100" />
                    <div className="h-3 w-1/2 rounded bg-slate-100" />
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && !error && total === 0 && (
            <div className="py-16 text-center text-slate-400">
              <div className="mb-3 text-5xl">🔍</div>
              <p className="font-medium">Không tìm thấy bài tập nào</p>
              <p className="text-sm">Thử từ khóa khác hoặc bỏ bớt bộ lọc.</p>
            </div>
          )}

          {!loading && page < pages && (
            <div className="mt-6 text-center">
              <button
                type="button"
                disabled={loading}
                onClick={() => {
                  if (loading) return;
                  const next = page + 1;
                  setPage(next);
                  load(next, true);
                }}
                className="rounded-xl border border-slate-200 bg-white px-6 py-3 font-semibold text-slate-700 shadow-soft transition hover:border-brand-400 hover:text-brand-600 disabled:cursor-not-allowed disabled:opacity-60"
              >
                Xem thêm bài tập
              </button>
            </div>
          )}
        </div>
      </div>

      <ExerciseDetailModal id={selected} onClose={() => setSelected(null)} />
    </section>
  );
}

function ExerciseDetailModal({
  id,
  onClose,
}: {
  id: number | null;
  onClose: () => void;
}) {
  const [data, setData] = useState<ExerciseDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (!id) {
      setData(null);
      return;
    }
    setLoading(true);
    setErr("");
    api
      .getExercise(id)
      .then(setData)
      .catch((e) => setErr((e as Error).message))
      .finally(() => setLoading(false));
  }, [id]);

  const steps =
    data && Array.isArray(data.instruction_steps_vi) && data.instruction_steps_vi.length
      ? data.instruction_steps_vi
      : data?.instruction_vi
        ? [data.instruction_vi]
        : [];

  const role = movementRoleLabel(data?.movement_role);
  const pattern = movementPatternLabel(data?.movement_pattern);
  const ytEmbed = youtubeEmbedUrl(data?.video_url);
  const directVideo = isDirectVideoUrl(data?.video_url) ? mediaUrl(data?.video_url) : null;

  return (
    <Modal open={!!id} onClose={onClose} size="wide">
      {loading && <div className="p-8 text-center text-slate-400">Đang tải…</div>}
      {err && <div className="p-8 text-center text-rose-500">Lỗi: {err}</div>}
      {data && (
        <>
          <div className="relative">
            {ytEmbed ? (
              <div className="aspect-video w-full bg-black">
                <iframe
                  title={data.name_vi}
                  src={ytEmbed}
                  className="h-full w-full"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            ) : directVideo ? (
              <video
                src={directVideo}
                controls
                muted
                playsInline
                className="aspect-video w-full bg-black object-contain"
              />
            ) : (
              <ExerciseThumb
                gif={data.gif_url}
                image={data.image_url}
                video={data.video_url}
                bodyPart={data.body_part}
                className="h-56"
                emojiSize="text-6xl"
              />
            )}
            <button
              onClick={onClose}
              className="absolute top-3 right-3 grid h-9 w-9 place-items-center rounded-full bg-white/90 text-xl leading-none text-slate-600 shadow"
            >
              ×
            </button>
          </div>
          <div className="p-5">
            <h2 className="text-xl leading-tight font-extrabold">{data.name_vi}</h2>
            {data.name_en && data.name_en !== data.name_vi && (
              <p className="mt-0.5 text-sm text-slate-400">{data.name_en}</p>
            )}

            <div className="mt-3 flex flex-wrap gap-1.5">
              {data.muscle_group && (
                <span className="badge badge-gray">
                  {muscleDisplayLabel(data.body_part, data.muscle_group)}
                </span>
              )}
              {role && <span className="badge badge-gray">{role.vi}</span>}
              {pattern && <span className="badge badge-gray">{pattern.vi}</span>}
              {data.venue && (
                <span className="badge badge-gray">{VENUE_LABEL[data.venue] || data.venue}</span>
              )}
              {data.is_beginner_friendly && <span className="badge badge-new">Phù hợp người mới</span>}
            </div>

            <dl className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs text-slate-400">Nhóm cơ</dt>
                <dd className="mt-0.5 font-semibold">
                  {muscleDisplayLabel(data.body_part, data.muscle_group || undefined) || "—"}
                </dd>
              </div>
              {!!data.secondary_muscles?.length && (
                <div className="rounded-xl bg-slate-50 p-3 sm:col-span-2">
                  <dt className="text-xs text-slate-400">Nhóm cơ phụ</dt>
                  <dd className="mt-1.5 flex flex-wrap gap-1.5">
                    {data.secondary_muscles.map((m) => (
                      <span key={m} className="badge badge-gray">
                        {m}
                      </span>
                    ))}
                  </dd>
                </div>
              )}
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs text-slate-400">Dụng cụ</dt>
                <dd className="mt-0.5 font-semibold">
                  {data.equipment && data.equipment !== "—" ? data.equipment : "Không cần dụng cụ"}
                </dd>
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs text-slate-400">Vai trò bài</dt>
                <dd className="mt-0.5 font-semibold">{role?.vi || "—"}</dd>
                {role && <dd className="mt-0.5 text-xs text-slate-400">{role.en}</dd>}
              </div>
              <div className="rounded-xl bg-slate-50 p-3">
                <dt className="text-xs text-slate-400">Mẫu chuyển động</dt>
                <dd className="mt-0.5 font-semibold">{pattern?.vi || "—"}</dd>
                {pattern && <dd className="mt-0.5 text-xs text-slate-400">{pattern.en}</dd>}
              </div>
            </dl>

            {data.notes_vi && !data.notes_vi.startsWith("seed:") && (
              <div className="mt-4 rounded-xl bg-amber-50 p-3 text-sm text-amber-950">
                <p className="font-bold">Ghi chú</p>
                <p className="mt-1 leading-relaxed">{data.notes_vi}</p>
              </div>
            )}

            {steps.length > 0 && (
              <div className="mt-4">
                <p className="mb-2 font-bold">Cách thực hiện</p>
                <ol className="list-inside list-decimal space-y-1.5 text-sm leading-relaxed text-slate-600">
                  {steps.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ol>
              </div>
            )}

            {splitCoachLines(data.common_mistakes_vi).length > 0 && (
              <div className="mt-4">
                <p className="mb-2 font-bold">Lỗi thường gặp</p>
                <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed text-slate-600">
                  {splitCoachLines(data.common_mistakes_vi).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            {splitCoachLines(data.tips_vi).length > 0 && (
              <div className="mt-4">
                <p className="mb-2 font-bold">Mẹo</p>
                <ul className="list-inside list-disc space-y-1.5 text-sm leading-relaxed text-slate-600">
                  {splitCoachLines(data.tips_vi).map((line, i) => (
                    <li key={i}>{line}</li>
                  ))}
                </ul>
              </div>
            )}

            {!steps.length && !data.common_mistakes_vi && !data.tips_vi && (
              <p className="mt-4 text-sm text-slate-400">
                Hướng dẫn chi tiết cho bài tập này đang được bổ sung.
              </p>
            )}
          </div>
        </>
      )}
    </Modal>
  );
}
