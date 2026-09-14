"use client";

import type { FoodCategory } from "@/lib/types";

type Props = {
  categories: FoodCategory[];
  allCount?: number;
  counts: Record<number, number>;
  selected: number | "";
  onSelect: (next: number | "") => void;
};

function label(name: string, count?: number) {
  return count == null ? name : `${name} ${count.toLocaleString("vi-VN")}`;
}

export default function FoodAisleChips({ categories, allCount, counts, selected, onSelect }: Props) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      <button
        type="button"
        className={`chip ${selected === "" ? "chip-active" : ""}`}
        onClick={() => onSelect("")}
      >
        {label("Tất cả", allCount)}
      </button>
      {categories.map((c) => (
        <button
          key={c.id}
          type="button"
          className={`chip ${selected === c.id ? "chip-active" : ""}`}
          onClick={() => onSelect(c.id)}
        >
          {label(c.name_vi, counts[c.id])}
        </button>
      ))}
    </div>
  );
}
