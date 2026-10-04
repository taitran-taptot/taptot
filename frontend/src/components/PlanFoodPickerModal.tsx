"use client";

import { useEffect, useState } from "react";
import Modal from "./Modal";
import { api } from "@/lib/api";
import { mediaUrl } from "@/lib/labels";
import { kcalPer100gFromFood } from "@/lib/mealGrams";
import { MEAL_GROUP_ORDER, MEAL_LABEL, type PlanMealType } from "@/lib/plansApi";
import type { Food, FoodCategory } from "@/lib/types";

export default function PlanFoodPickerModal({
  open,
  onClose,
  onPick,
  initialMealType = "lunch",
  hideMealSelect = false,
}: {
  open: boolean;
  onClose: () => void;
  onPick: (food: Food, mealType: PlanMealType) => void;
  initialMealType?: PlanMealType;
  hideMealSelect?: boolean;
}) {
  const [q, setQ] = useState("");
  const [mealType, setMealType] = useState<PlanMealType>(initialMealType);
  const [categoryId, setCategoryId] = useState<number | "">("");
  const [cats, setCats] = useState<FoodCategory[]>([]);
  const [items, setItems] = useState<Food[]>([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setQ("");
    setPage(1);
    setCategoryId("");
    setMealType(initialMealType);
    api
      .foodCategories()
      .then((d) => setCats(d.items || []))
      .catch(() => setCats([]));
  }, [open, initialMealType]);

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => {
      setLoading(true);
      api
        .searchFoods({
          q: q || undefined,
          category_id: categoryId === "" ? undefined : categoryId,
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
  }, [q, categoryId, open]);

  async function loadMore() {
    const next = page + 1;
    setLoading(true);
    try {
      const d = await api.searchFoods({
        q: q || undefined,
        category_id: categoryId === "" ? undefined : categoryId,
        page: next,
        page_size: 18,
      });
      setItems((prev) => [...prev, ...d.items]);
      setPages(d.pages);
      setPage(next);
    } catch {
      /* keep */
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal open={open} onClose={onClose} size="wide" lockScroll title="Thêm món">
      <div className="flex min-h-0 flex-1 flex-col" style={{ maxHeight: "min(92vh, 800px)" }}>
        <div className="shrink-0 border-b border-slate-100 px-4 pb-3 pt-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-base font-bold sm:text-lg">Kho món ăn</h3>
              <p className="mt-1 text-xs text-slate-400">
                {hideMealSelect ? "Bấm thẻ để thêm vào tổng lượng ngày." : "Chọn bữa rồi bấm thẻ để thêm."}
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
              placeholder="Tìm món… (vd: ức gà, cơm, rau)"
              className="field flex-1"
            />
            <select
              value={categoryId}
              onChange={(e) => setCategoryId(e.target.value === "" ? "" : Number(e.target.value))}
              className="field sm:w-40"
              aria-label="Lọc loại thực phẩm"
            >
              <option value="">Mọi loại</option>
              {cats.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name_vi}
                </option>
              ))}
            </select>
            {!hideMealSelect && (
            <select
              value={mealType}
              onChange={(e) => setMealType(e.target.value as PlanMealType)}
              className="field sm:w-36"
            >
              {MEAL_GROUP_ORDER.map((k) => (
                <option key={k} value={k}>
                  {MEAL_LABEL[k]}
                </option>
              ))}
            </select>
            )}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 py-3">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {items.map((f) => {
              const thumb = mediaUrl(f.image_url);
              return (
                <button
                  key={f.id}
                  type="button"
                      onClick={() => onPick(f, hideMealSelect ? "flex" : mealType)}
                  className="overflow-hidden rounded-2xl bg-white text-left shadow-soft ring-1 ring-slate-100 transition hover:-translate-y-0.5 hover:ring-amber-200"
                >
                  <span className="relative block h-28 w-full overflow-hidden bg-gradient-to-br from-amber-100 to-orange-50">
                    {thumb ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={thumb} alt="" className="h-full w-full object-cover" loading="lazy" />
                    ) : (
                      <span className="grid h-full place-items-center text-3xl">🍽️</span>
                    )}
                  </span>
                  <div className="p-2.5">
                    <p className="line-clamp-2 text-sm font-bold leading-snug text-slate-800">{f.name_vi}</p>
                    <p className="mt-1 text-[11px] font-semibold text-amber-800">
                      {Math.round(kcalPer100gFromFood(f))} kcal/100g · + Thêm
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
          {loading && <p className="py-6 text-center text-sm text-slate-400">Đang tải…</p>}
          {!loading && items.length === 0 && (
            <p className="py-8 text-center text-sm text-slate-400">Không thấy món phù hợp.</p>
          )}
          {!loading && page < pages && (
            <div className="mt-4 text-center">
              <button
                type="button"
                onClick={() => void loadMore()}
                className="rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 hover:border-amber-400"
              >
                Xem thêm
              </button>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}
