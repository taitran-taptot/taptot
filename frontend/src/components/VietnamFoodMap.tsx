"use client";

import { useEffect, useState, type MouseEvent } from "react";
import type { FoodRegionSlug } from "@/lib/types";
import { FOOD_REGION_LABELS } from "@/lib/types";

export type VietnamMapMode = "nationwide" | "region";

export type MapProvinceClick = {
  id: string;
  name: string;
  region: FoodRegionSlug | string;
};

type MapFeature = {
  id: string;
  name: string;
  region: FoodRegionSlug | string;
  d: string;
};

type MapData = {
  viewBox: string;
  features: MapFeature[];
};

type Props = {
  mode: VietnamMapMode;
  activeProvinceId?: string | null;
  dishLabel?: string | null;
  dishCountByProvince?: Record<string, number>;
  onProvinceClick?: (info: MapProvinceClick) => void;
  className?: string;
};

function provinceFill(
  featureId: string,
  mode: VietnamMapMode,
  activeProvinceId?: string | null,
): string {
  if (mode === "nationwide") return "#38bdf8";
  if (activeProvinceId && featureId === activeProvinceId) return "#f97316";
  return "#e2e8f0";
}

function featureFromPath(
  svg: SVGSVGElement,
  features: MapFeature[],
  clientX: number,
  clientY: number,
): MapFeature | null {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const loc = pt.matrixTransform(ctm.inverse());

  const paths = svg.querySelectorAll<SVGGeometryElement>("path[data-province-id]");
  for (const path of paths) {
    try {
      if (path.isPointInFill(loc) || path.isPointInStroke(loc)) {
        const id = path.dataset.provinceId;
        return features.find((f) => f.id === id) ?? null;
      }
    } catch {
      /* some browsers throw on isPointInFill with detached CTM */
    }
  }

  const el = document.elementFromPoint(clientX, clientY);
  const path = el?.closest?.("path[data-province-id]");
  if (path instanceof SVGElement) {
    const id = path.dataset.provinceId;
    return features.find((f) => f.id === id) ?? null;
  }
  return null;
}

export default function VietnamFoodMap({
  mode,
  activeProvinceId = null,
  dishLabel = null,
  dishCountByProvince = {},
  onProvinceClick,
  className = "",
}: Props) {
  const [data, setData] = useState<MapData | null>(null);
  const [loadError, setLoadError] = useState("");
  const [hoverId, setHoverId] = useState<string | null>(null);
  const clickable = Boolean(onProvinceClick);

  useEffect(() => {
    let cancelled = false;
    fetch("/maps/vietnam-food-map.json")
      .then((r) => {
        if (!r.ok) throw new Error("Không tải được bản đồ");
        return r.json();
      })
      .then((json: MapData) => {
        if (!cancelled) setData(json);
      })
      .catch((e) => {
        if (!cancelled) setLoadError((e as Error).message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const hoverFeature = data?.features.find((f) => f.id === hoverId) ?? null;
  const activeFeature = data?.features.find((f) => f.id === activeProvinceId) ?? null;
  const hoverCount = hoverFeature ? dishCountByProvince[hoverFeature.id] || 0 : 0;
  const activeCount = activeFeature ? dishCountByProvince[activeFeature.id] || 0 : 0;

  function handleSvgClick(e: MouseEvent<SVGSVGElement>) {
    if (!onProvinceClick || !data) return;
    const feature = featureFromPath(e.currentTarget, data.features, e.clientX, e.clientY);
    if (!feature) return;
    onProvinceClick({ id: feature.id, name: feature.name, region: feature.region });
  }

  return (
    <div className={`relative overflow-hidden rounded-2xl bg-[#f8f5ef] ${className}`}>
      {loadError && <p className="p-6 text-center text-sm text-rose-600">{loadError}</p>}
      {!data && !loadError && (
        <div className="grid min-h-[28rem] place-items-center text-sm text-slate-400">Đang tải bản đồ…</div>
      )}
      {data && (
        <svg
          viewBox={data.viewBox}
          className={`mx-auto h-full w-full max-h-[min(72vh,680px)] ${clickable ? "cursor-pointer" : ""}`}
          role="group"
          aria-label="Bản đồ hành chính Việt Nam gồm các tỉnh thành, Hoàng Sa và Trường Sa"
          onClick={handleSvgClick}
        >
          <title>Bản đồ Việt Nam — bấm một tỉnh để xem món</title>
          {data.features.map((f) => {
            const active = mode === "nationwide" || activeProvinceId === f.id;
            const hovered = hoverId === f.id;
            const n = dishCountByProvince[f.id] || 0;
            return (
              <path
                key={f.id}
                data-province-id={f.id}
                d={f.d}
                fill={provinceFill(f.id, mode, activeProvinceId)}
                stroke="#0f172a"
                strokeWidth={hovered || activeProvinceId === f.id ? 1.35 : 0.55}
                strokeLinejoin="round"
                role={clickable ? "button" : undefined}
                tabIndex={clickable ? 0 : undefined}
                aria-label={`${f.name}${n ? ` · ${n} món` : ""}`}
                className={`${clickable ? "cursor-pointer" : ""} ${
                  active ? "opacity-100" : "opacity-80"
                } transition-[fill,opacity] duration-200`}
                style={{ pointerEvents: "fill" }}
                onMouseEnter={() => setHoverId(f.id)}
                onMouseLeave={() => setHoverId(null)}
                onClick={(ev) => {
                  ev.stopPropagation();
                  onProvinceClick?.({ id: f.id, name: f.name, region: f.region });
                }}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    onProvinceClick?.({ id: f.id, name: f.name, region: f.region });
                  }
                }}
              >
                <title>
                  {f.name}
                  {n ? ` · ${n} món` : ""}
                  {FOOD_REGION_LABELS[f.region as FoodRegionSlug]
                    ? ` — ${FOOD_REGION_LABELS[f.region as FoodRegionSlug]}`
                    : ""}
                </title>
              </path>
            );
          })}
        </svg>
      )}

      {dishLabel && activeFeature && (
        <div className="pointer-events-none absolute top-3 left-3 max-w-[70%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200">
          <span className="block text-sm font-extrabold text-orange-700">{dishLabel}</span>
          <span className="mt-0.5 block font-medium text-slate-500">{activeFeature.name}</span>
        </div>
      )}
      {!dishLabel && activeFeature && clickable && (
        <div className="pointer-events-none absolute top-3 left-3 max-w-[70%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200">
          <span className="block text-sm font-extrabold text-orange-700">{activeFeature.name}</span>
          <span className="mt-0.5 block font-medium text-slate-500">
            {activeCount > 0 ? `${activeCount} món truyền thống` : "Chưa có món cho tỉnh này"}
          </span>
        </div>
      )}
      {hoverFeature && hoverFeature.id !== activeProvinceId && (
        <div
          className={`pointer-events-none absolute left-3 max-w-[70%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200 ${
            dishLabel && activeFeature ? "top-[4.25rem]" : activeFeature && clickable ? "top-[4.25rem]" : "top-3"
          }`}
        >
          {hoverFeature.name}
          <span className="mt-0.5 block font-medium text-slate-500">
            {hoverCount > 0
              ? `${hoverCount} món`
              : FOOD_REGION_LABELS[hoverFeature.region as FoodRegionSlug] || hoverFeature.region}
          </span>
        </div>
      )}

      <div className="pointer-events-none absolute right-3 bottom-3 rounded-xl bg-white/95 px-3 py-2 text-[10px] shadow-soft ring-1 ring-slate-200">
        <p className="mb-1.5 font-bold text-slate-700">Chú thích</p>
        <div className="flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-sm bg-[#38bdf8] ring-1 ring-slate-400" />
          <span className="text-slate-600">Toàn quốc / thực phẩm</span>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className="inline-block h-3 w-3 rounded-sm bg-[#f97316] ring-1 ring-slate-400" />
          <span className="text-slate-600">Tỉnh đang chọn</span>
        </div>
      </div>
    </div>
  );
}
