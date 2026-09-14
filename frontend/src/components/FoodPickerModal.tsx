"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Modal from "./Modal";
import FoodAisleChips from "./FoodAisleChips";
import { api } from "@/lib/api";
import { PAGE_SIZE } from "@/lib/config";
import { foodDisplayName, foodKcalLine, foodRoleLabel, loadFoodAisleCounts } from "@/lib/foodDisplay";
import type { Food, FoodCategory } from "@/lib/types";

type RoleFilter = "" | "protein" | "carb" | "produce";

type Props = {
  open: boolean;
  onClose: () => void;
  selected: Record<number, Food>;
  onSave: (next: Record<number, Food>) => void;
  excludeRaw?: boolean;
  showRoleFilters?: boolean;
};

export default function FoodPickerModal({
  open,
  onClose,
  selected,
  onSave,
  excludeRaw = false,
  showRoleFilters = false,
}: Props) {
  const [q, setQ] = useState("");
  const [category, setCategory] = useState<number | "">("");
  const [role, setRole] = useState<RoleFilter>("");
  const [cats, setCats] = useState<FoodCategory[]>([]);
  const [allCount, setAllCount] = useState<number>();
  const [aisleCounts, setAisleCounts] = useState<Record<number, number>>({});
  const [items, setItems] = useState<Food[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [draft, setDraft] = useState<Record<number, Food>>({});
  const skipSearchRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    setDraft({ ...selected });
    setQ("");
    setCategory("");
    setError("");
    setLoading(true);
    skipSearchRef.current = true;
    setRole("");
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- sync draft on open

  useEffect(() => {
    if (!open) return;
    api
      .foodCategories()
      .then(async (d) => {
        const sorted = [...d.items].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
        setCats(sorted);
        const aisle = await loadFoodAisleCounts(sorted);
        setAllCount(aisle.all);
        setAisleCounts(aisle.counts);
      })
      .catch(() => {});
  }, [open]);

  const load = useCallback(
    async (nextPage: number, append: boolean, query: string, cat: number | "", roleFilter: RoleFilter) => {
      setLoading(true);
      setError("");
      try {
        const data = await api.searchFoods({
          q: query,
          category_id: cat === "" ? undefined : cat,
          page: nextPage,
          page_size: PAGE_SIZE,
          exclude_raw: excludeRaw || undefined,
          macro_role: roleFilter || undefined,
        });
        setTotal(data.total);
        setPages(data.pages);
        setItems((prev) => (append ? [...prev, ...data.items] : data.items));
      } catch (e) {
        setError((e as Error).message || "Không tải được kho thức ăn.");
      } finally {
        setLoading(false);
      }
    },
    [excludeRaw],
  );

  useEffect(() => {
    if (!open) return;
    if (skipSearchRef.current) {
      skipSearchRef.current = false;
      setPage(1);
      void load(1, false, "", "", role);
      return;
    }
    const t = setTimeout(() => {
      setPage(1);
      void load(1, false, q, category, role);
    }, 300);
    return () => clearTimeout(t);
  }, [q, category, role, open, load]);

  function toggle(food: Food) {
    setDraft((prev) => {
      const next = { ...prev };
      if (next[food.id]) delete next[food.id];
      else next[food.id] = food;
      return next;
    });
  }

  function confirm() {
    onSave(draft);
    onClose();
  }

  const selectedCount = Object.keys(draft).length;

  return (
    <Modal open={open} onClose={onClose} size="wide" lockScroll>
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 800px)" }}>
        <div className="shrink-0 border-b border-slate-100 px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-bold sm:text-lg">Kho nguyên liệu</h3>
              <p className="mt-1 text-xs text-slate-400">
                Đã chọn <b className="text-brand-600">{selectedCount}</b>
                {excludeRaw ? " · không hiện nguyên liệu sống" : " · thịt, rau, cơm, khoai"}
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
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            type="search"
            placeholder="Tìm… (vd: ức gà, cơm, chuối)"
            className="field mt-3"
          />
          {showRoleFilters && (
            <div className="mt-3 flex flex-wrap gap-2">
              {(
                [
                  ["", "Tất cả vai trò"],
                  ["protein", "Đạm"],
                  ["carb", "Tinh bột"],
                  ["produce", "Rau"],
                ] as const
              ).map(([id, label]) => (
                <button
                  key={id || "all-role"}
                  type="button"
                  className={`chip ${role === id ? "chip-active" : ""}`}
                  onClick={() => setRole(id)}
                >
                  {label}
                </button>
              ))}
            </div>
          )}
          <FoodAisleChips
            categories={cats}
            allCount={allCount}
            counts={aisleCounts}
            selected={category}
            onSelect={setCategory}
          />
          {total > 0 && (
            <p className="mt-2 text-xs text-slate-400">{total.toLocaleString("vi-VN")} nguyên liệu</p>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
          {error && <p className="mb-3 rounded-lg bg-rose-50 px-3 py-2 text-sm text-rose-600">{error}</p>}
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            {items.map((f) => {
              const on = !!draft[f.id];
              const roleLabel = foodRoleLabel(f);
              return (
                <button
                  key={f.id}
                  type="button"
                  onClick={() => toggle(f)}
                  className={`rounded-xl px-3 py-2.5 text-left ring-1 transition ${
                    on ? "bg-brand-50 ring-brand-300" : "bg-white ring-slate-200 hover:ring-brand-200"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="clamp-2 text-sm font-bold leading-snug">{foodDisplayName(f.name_vi)}</p>
                    <span
                      className={`grid h-5 w-5 shrink-0 place-items-center rounded border text-[11px] font-bold ${
                        on ? "border-brand-500 bg-brand-500 text-white" : "border-slate-300 text-transparent"
                      }`}
                    >
                      ✓
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">
                    {roleLabel ? `${roleLabel} · ` : ""}
                    {foodKcalLine(f)}
                  </p>
                </button>
              );
            })}
          </div>
          {loading && <p className="py-6 text-center text-sm text-slate-400">Đang tải…</p>}
          {!loading && !error && items.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-400">Thử ức gà, cơm trắng, chuối.</p>
          )}
          {!loading && page < pages && (
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => {
                  const next = page + 1;
                  setPage(next);
                  void load(next, true, q, category, role);
                }}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-brand-400 hover:text-brand-600"
              >
                Xem thêm
              </button>
            </div>
          )}
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
            Lưu lựa chọn ({selectedCount})
          </button>
        </div>
      </div>
    </Modal>
  );
}
