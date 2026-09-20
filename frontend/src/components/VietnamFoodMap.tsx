"use client";

import { useEffect, useRef, useState, type PointerEvent, type ReactNode } from "react";
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

type Box = { x: number; y: number; w: number; h: number };
type Cam = { scale: number; vx: number; vy: number };

type Props = {
  mode: VietnamMapMode;
  activeProvinceId?: string | null;
  dishLabel?: string | null;
  dishCountByProvince?: Record<string, number>;
  onProvinceClick?: (info: MapProvinceClick) => void;
  className?: string;
};

const MIN_SCALE = 1;
const MAX_SCALE = 8;
const ZOOM_STEP = 1.4;
const PAN_THRESHOLD = 8;

function normProvinceId(id?: string | null): string {
  if (!id) return "";
  const t = id.trim();
  return /^\d+$/.test(t) ? t.padStart(2, "0") : t;
}

function countForProvince(id: string, counts: Record<string, number>): number {
  const key = normProvinceId(id);
  if (counts[id]) return counts[id];
  if (counts[key]) return counts[key];
  const unpadded = id.replace(/^0+/, "");
  if (unpadded && counts[unpadded]) return counts[unpadded];
  return 0;
}

const ISLAND_FEATURE_IDS = new Set(["hoang-sa", "truong-sa"]);

function provinceFill(
  featureId: string,
  mode: VietnamMapMode,
  activeProvinceId: string | null | undefined,
  count: number,
): string {
  const isIsland = ISLAND_FEATURE_IDS.has(featureId);
  if (mode === "nationwide") return isIsland ? "#14532d" : "#16a34a";
  if (activeProvinceId && normProvinceId(featureId) === normProvinceId(activeProvinceId)) {
    return isIsland ? "#c2410c" : "#ea580c";
  }
  if (isIsland) {
    if (count <= 0) return "#57534e";
    if (count === 1) return "#166534";
    return "#14532d";
  }
  if (count <= 0) return "#e8e4dc";
  if (count === 1) return "#bbf7d0";
  if (count <= 3) return "#4ade80";
  return "#16a34a";
}

function expandIslandPath(d: string, scale = 1.25): string {
  const rings = d.match(/M[^M]*/g);
  if (!rings) return d;
  return rings
    .map((ring) => {
      const pairs: [number, number][] = [];
      const re = /(-?\d*\.?\d+)\s+(-?\d*\.?\d+)/g;
      let m: RegExpExecArray | null;
      while ((m = re.exec(ring))) {
        pairs.push([Number(m[1]), Number(m[2])]);
      }
      if (pairs.length < 3) return ring;
      const cx = pairs.reduce((sum, p) => sum + p[0], 0) / pairs.length;
      const cy = pairs.reduce((sum, p) => sum + p[1], 0) / pairs.length;
      return (
        pairs
          .map((p, i) => {
            const x = (p[0] - cx) * scale + cx;
            const y = (p[1] - cy) * scale + cy;
            return `${i === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
          })
          .join("") + "Z"
      );
    })
    .join(" ");
}

function parseBox(viewBox: string): Box {
  const [x, y, w, h] = viewBox.split(/[\s,]+/).map(Number);
  return { x: x || 0, y: y || 0, w: w || 420, h: h || 560 };
}

function clampCam(cam: Cam, base: Box): Cam {
  const scale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, cam.scale));
  const w = base.w / scale;
  const h = base.h / scale;
  return {
    scale,
    vx: Math.min(base.x + base.w - w, Math.max(base.x, cam.vx)),
    vy: Math.min(base.y + base.h - h, Math.max(base.y, cam.vy)),
  };
}

function clientToSvg(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number } | null {
  const ctm = svg.getScreenCTM();
  if (!ctm) return null;
  const pt = svg.createSVGPoint();
  pt.x = clientX;
  pt.y = clientY;
  const loc = pt.matrixTransform(ctm.inverse());
  return { x: loc.x, y: loc.y };
}

function featureFromPath(
  svg: SVGSVGElement,
  features: MapFeature[],
  clientX: number,
  clientY: number,
): MapFeature | null {
  const loc = clientToSvg(svg, clientX, clientY);
  if (loc) {
    const shapes = svg.querySelectorAll<SVGGeometryElement>("[data-province-id]");
    for (const shape of shapes) {
      try {
        const pt = svg.createSVGPoint();
        pt.x = loc.x;
        pt.y = loc.y;
        if (shape.isPointInFill(pt) || shape.isPointInStroke(pt)) {
          const id = shape.dataset.provinceId;
          return features.find((f) => f.id === id) ?? null;
        }
      } catch {
        /* some browsers throw on isPointInFill with detached CTM */
      }
    }
  }

  const el = document.elementFromPoint(clientX, clientY);
  const hit = el?.closest?.("[data-province-id]");
  if (hit instanceof SVGElement) {
    const id = hit.dataset.provinceId;
    return features.find((f) => f.id === id) ?? null;
  }
  return null;
}

function ZoomButton({
  label,
  disabled,
  onClick,
  children,
}: {
  label: string;
  disabled?: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      disabled={disabled}
      onClick={onClick}
      className="grid h-11 w-11 place-items-center rounded-xl bg-white/95 text-lg font-bold text-slate-700 shadow-soft ring-1 ring-slate-200 hover:bg-white disabled:opacity-35"
    >
      {children}
    </button>
  );
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
  const [cam, setCam] = useState<Cam>({ scale: 1, vx: 0, vy: 0 });
  const [panning, setPanning] = useState(false);
  const clickable = Boolean(onProvinceClick);

  const wrapRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const dataRef = useRef(data);
  const camRef = useRef(cam);
  const ptrs = useRef(new Map<number, { x: number; y: number }>());
  const pan = useRef<{ x: number; y: number; vx: number; vy: number } | null>(null);
  const pinch = useRef<{ dist: number } | null>(null);
  const moved = useRef(false);
  const lastTap = useRef(0);

  dataRef.current = data;
  camRef.current = cam;

  const base = data ? parseBox(data.viewBox) : { x: 0, y: 0, w: 420, h: 560 };
  const viewW = base.w / cam.scale;
  const viewH = base.h / cam.scale;
  const liveViewBox = `${cam.vx} ${cam.vy} ${viewW} ${viewH}`;

  useEffect(() => {
    let cancelled = false;
    fetch("/maps/vietnam-food-map.json?v=qn1")
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

  function applyCam(next: Cam) {
    const map = dataRef.current;
    if (!map) return;
    const clamped = clampCam(next, parseBox(map.viewBox));
    camRef.current = clamped;
    setCam(clamped);
  }

  function zoomAt(clientX: number, clientY: number, factor: number) {
    const svg = svgRef.current;
    const map = dataRef.current;
    if (!svg || !map) return;
    const box = parseBox(map.viewBox);
    const current = camRef.current;
    const loc = clientToSvg(svg, clientX, clientY);
    if (!loc) return;
    const w = box.w / current.scale;
    const h = box.h / current.scale;
    const nextScale = Math.min(MAX_SCALE, Math.max(MIN_SCALE, current.scale * factor));
    const nw = box.w / nextScale;
    const nh = box.h / nextScale;
    applyCam({
      scale: nextScale,
      vx: loc.x - ((loc.x - current.vx) * nw) / w,
      vy: loc.y - ((loc.y - current.vy) * nh) / h,
    });
  }

  function zoomTowardCenter(factor: number) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    zoomAt(rect.left + rect.width / 2, rect.top + rect.height / 2, factor);
  }

  function resetCam() {
    applyCam({ scale: 1, vx: base.x, vy: base.y });
  }

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoomAt(e.clientX, e.clientY, e.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP);
    };
    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, []);

  function handlePointerDown(e: PointerEvent<HTMLDivElement>) {
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if ((e.target as HTMLElement).closest("button")) return;
    wrapRef.current?.setPointerCapture(e.pointerId);
    ptrs.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    moved.current = false;
    if (ptrs.current.size === 1) {
      pinch.current = null;
      pan.current = { x: e.clientX, y: e.clientY, vx: camRef.current.vx, vy: camRef.current.vy };
      setPanning(true);
    } else if (ptrs.current.size >= 2) {
      pan.current = null;
      const [a, b] = [...ptrs.current.values()];
      pinch.current = { dist: Math.hypot(a.x - b.x, a.y - b.y) };
    }
  }

  function handlePointerMove(e: PointerEvent<HTMLDivElement>) {
    if (!ptrs.current.has(e.pointerId)) return;
    ptrs.current.set(e.pointerId, { x: e.clientX, y: e.clientY });
    const svg = svgRef.current;
    const map = dataRef.current;
    if (!svg || !map) return;
    const box = parseBox(map.viewBox);
    const rect = svg.getBoundingClientRect();

    if (ptrs.current.size >= 2 && pinch.current) {
      const [a, b] = [...ptrs.current.values()];
      const dist = Math.hypot(a.x - b.x, a.y - b.y);
      if (dist > 10 && pinch.current.dist > 10) {
        moved.current = true;
        zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, dist / pinch.current.dist);
        pinch.current = { dist };
      }
      return;
    }

    if (pan.current && ptrs.current.size === 1) {
      const dx = e.clientX - pan.current.x;
      const dy = e.clientY - pan.current.y;
      if (Math.hypot(dx, dy) > PAN_THRESHOLD) moved.current = true;
      const scale = camRef.current.scale;
      const w = box.w / scale;
      const h = box.h / scale;
      applyCam({
        scale,
        vx: pan.current.vx - dx * (w / rect.width),
        vy: pan.current.vy - dy * (h / rect.height),
      });
    }
  }

  function handlePointerUp(e: PointerEvent<HTMLDivElement>) {
    ptrs.current.delete(e.pointerId);
    if (ptrs.current.size < 2) pinch.current = null;
    if (ptrs.current.size === 1) {
      const remain = [...ptrs.current.values()][0];
      pan.current = { x: remain.x, y: remain.y, vx: camRef.current.vx, vy: camRef.current.vy };
    }
    if (ptrs.current.size > 0) return;
    pan.current = null;
    setPanning(false);

    const wasMoved = moved.current;
    moved.current = false;
    if (wasMoved || !onProvinceClick || !data || !svgRef.current) return;

    const now = Date.now();
    if (now - lastTap.current < 280) {
      lastTap.current = 0;
      zoomAt(e.clientX, e.clientY, ZOOM_STEP);
      return;
    }
    lastTap.current = now;

    const feature = featureFromPath(svgRef.current, data.features, e.clientX, e.clientY);
    if (feature) onProvinceClick({ id: feature.id, name: feature.name, region: feature.region });
  }

  const hoverFeature = data?.features.find((f) => f.id === hoverId) ?? null;
  const activeFeature =
    data?.features.find((f) => normProvinceId(f.id) === normProvinceId(activeProvinceId)) ?? null;
  const hoverCount = hoverFeature ? countForProvince(hoverFeature.id, dishCountByProvince) : 0;
  const activeCount = activeFeature ? countForProvince(activeFeature.id, dishCountByProvince) : 0;
  const canZoomIn = cam.scale < MAX_SCALE - 0.01;
  const canZoomOut = cam.scale > MIN_SCALE + 0.01;

  return (
    <div
      ref={wrapRef}
      className={`relative overflow-hidden rounded-2xl bg-[#f8f5ef] touch-none ${className} ${
        panning ? "cursor-grabbing" : "cursor-grab"
      }`}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
    >
      {loadError && <p className="p-6 text-center text-sm text-rose-600">{loadError}</p>}
      {!data && !loadError && (
        <div className="grid h-full min-h-[inherit] place-items-center text-sm text-slate-400">Đang tải bản đồ…</div>
      )}
      {data && (
        <svg
          ref={svgRef}
          viewBox={liveViewBox}
          className="mx-auto h-full w-full"
          role="group"
          aria-label="Bản đồ hành chính Việt Nam gồm các tỉnh thành, Hoàng Sa và Trường Sa. Vuốt để kéo, chụm để phóng to."
        >
          <title>Bản đồ Việt Nam — phóng to rồi bấm một tỉnh để xem món</title>
          {data.features.map((f) => {
            const isActive = normProvinceId(f.id) === normProvinceId(activeProvinceId);
            const hovered = hoverId === f.id;
            const n = countForProvince(f.id, dishCountByProvince);
            const isIsland = ISLAND_FEATURE_IDS.has(f.id);
            const fill = provinceFill(f.id, mode, activeProvinceId, n);
            return (
              <path
                key={f.id}
                data-province-id={f.id}
                d={isIsland ? expandIslandPath(f.d) : f.d}
                fill={fill}
                fillRule="nonzero"
                stroke={isIsland ? "#052e16" : "#0f172a"}
                strokeWidth={isIsland ? (hovered || isActive ? 1.4 : 0.9) : hovered || isActive ? 1.6 : 0.55}
                strokeLinejoin="round"
                strokeLinecap="round"
                role={clickable ? "button" : undefined}
                tabIndex={clickable ? 0 : undefined}
                aria-label={`${f.name}${n ? ` · ${n} món` : " · chưa có món"}`}
                className={`${clickable ? "cursor-pointer" : ""} opacity-100`}
                style={{ pointerEvents: "fill", paintOrder: "stroke fill" }}
                onMouseEnter={() => setHoverId(f.id)}
                onMouseLeave={() => setHoverId(null)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    onProvinceClick?.({ id: f.id, name: f.name, region: f.region });
                  }
                }}
              >
                <title>
                  {f.name}
                  {n ? ` · ${n} món` : " · chưa có món"}
                  {FOOD_REGION_LABELS[f.region as FoodRegionSlug]
                    ? ` — ${FOOD_REGION_LABELS[f.region as FoodRegionSlug]}`
                    : ""}
                </title>
              </path>
            );
          })}
        </svg>
      )}

      <div className="absolute top-2 right-2 z-20 flex flex-col gap-1.5">
        <ZoomButton label="Phóng to" disabled={!canZoomIn} onClick={() => zoomTowardCenter(ZOOM_STEP)}>
          +
        </ZoomButton>
        <ZoomButton label="Thu nhỏ" disabled={!canZoomOut} onClick={() => zoomTowardCenter(1 / ZOOM_STEP)}>
          −
        </ZoomButton>
        <ZoomButton label="Toàn cảnh" disabled={!canZoomOut} onClick={resetCam}>
          <span className="text-[10px] font-extrabold leading-none">1x</span>
        </ZoomButton>
      </div>

      {mode === "nationwide" && dishLabel && (
        <div className="pointer-events-none absolute top-3 left-3 max-w-[62%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200">
          <span className="block text-sm font-extrabold text-brand-700">{dishLabel}</span>
          <span className="mt-0.5 block font-medium text-slate-500">Cả nước</span>
        </div>
      )}
      {mode !== "nationwide" && dishLabel && activeFeature && (
        <div className="pointer-events-none absolute top-3 left-3 max-w-[62%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200">
          <span className="block text-sm font-extrabold text-orange-700">{dishLabel}</span>
          <span className="mt-0.5 block font-medium text-slate-500">{activeFeature.name}</span>
        </div>
      )}
      {mode !== "nationwide" && !dishLabel && activeFeature && clickable && (
        <div className="pointer-events-none absolute top-3 left-3 max-w-[62%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200">
          <span className="block text-sm font-extrabold text-orange-700">{activeFeature.name}</span>
          <span className="mt-0.5 block font-medium text-slate-500">
            {activeCount > 0 ? `${activeCount} món truyền thống` : "Chưa có món cho tỉnh này"}
          </span>
        </div>
      )}
      {hoverFeature && hoverFeature.id !== activeFeature?.id && (
        <div
          className={`pointer-events-none absolute left-3 max-w-[62%] rounded-lg bg-white/95 px-2.5 py-1.5 text-xs font-semibold text-slate-800 shadow-soft ring-1 ring-slate-200 ${
            (mode === "nationwide" && dishLabel) ||
            (mode !== "nationwide" && (dishLabel || activeFeature) && clickable)
              ? "top-[4.25rem]"
              : "top-3"
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

      <div className="pointer-events-none absolute bottom-3 left-3 rounded-xl bg-white/95 px-3 py-2 text-[10px] shadow-soft ring-1 ring-slate-200">
        <p className="mb-1.5 font-bold text-slate-700">Chú thích</p>
        {mode === "nationwide" ? (
          <div className="flex items-center gap-2">
            <span className="inline-block h-3 w-3 rounded-sm bg-[#16a34a] ring-1 ring-slate-400" />
            <span className="text-slate-600">Cả nước</span>
          </div>
        ) : (
          <>
            <div className="flex items-center gap-2">
              <span className="flex overflow-hidden rounded-sm ring-1 ring-slate-400">
                <span className="inline-block h-3 w-2.5 bg-[#bbf7d0]" />
                <span className="inline-block h-3 w-2.5 bg-[#4ade80]" />
                <span className="inline-block h-3 w-2.5 bg-[#16a34a]" />
              </span>
              <span className="text-slate-600">Nhiều món hơn</span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-sm bg-[#e8e4dc] ring-1 ring-slate-400" />
              <span className="text-slate-600">Chưa có món</span>
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-sm bg-[#ea580c] ring-1 ring-slate-400" />
              <span className="text-slate-600">Tỉnh đang chọn</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
