"use client";

import { useEffect, useRef, useState } from "react";
import { mediaUrl } from "@/lib/labels";

function loopSpan(el: HTMLDivElement) {
  const cards = el.querySelectorAll("article");
  const count = cards.length / 3;
  if (count < 1) return 0;
  const start = cards[0] as HTMLElement;
  const next = cards[count] as HTMLElement | undefined;
  if (!next) return 0;
  return next.offsetLeft - start.offsetLeft;
}

function activeSlide(el: HTMLDivElement): { index: number; distance: number } {
  const cards = el.querySelectorAll("article");
  let best = 0;
  let bestDist = Number.POSITIVE_INFINITY;
  cards.forEach((card) => {
    const node = card as HTMLElement;
    const dist = Math.abs(node.offsetLeft - el.scrollLeft);
    if (dist < bestDist) {
      bestDist = dist;
      const value = Number(node.dataset.slide);
      best = Number.isFinite(value) ? value : 0;
    }
  });
  return { index: best, distance: bestDist };
}

export default function ProductDetailGallery({ urls, name }: { urls: string[]; name: string }) {
  const scroller = useRef<HTMLDivElement>(null);
  const shown = useRef(0);
  const hold = useRef(0);
  const [index, setIndex] = useState(0);
  const visible = urls.map((url) => url.trim()).filter(Boolean);

  useEffect(() => {
    const el = scroller.current;
    if (!el || visible.length < 2) return;
    const place = () => {
      const span = loopSpan(el);
      if (span > 0) el.scrollLeft = span;
    };
    place();
    const commit = () => {
      const span = loopSpan(el);
      if (span > 0) {
        if (el.scrollLeft < span - 1) el.scrollLeft += span;
        else if (el.scrollLeft >= span * 2 - 1) el.scrollLeft -= span;
      }
      const snapped = activeSlide(el);
      if (Date.now() < hold.current || snapped.distance > 24) return;
      shown.current = snapped.index;
      setIndex(snapped.index);
    };
    let timer = 0;
    const onScroll = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(commit, 180);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    el.addEventListener("scrollend", commit);
    window.addEventListener("resize", place);
    return () => {
      window.clearTimeout(timer);
      el.removeEventListener("scroll", onScroll);
      el.removeEventListener("scrollend", commit);
      window.removeEventListener("resize", place);
    };
  }, [visible.length]);

  if (!visible.length) return null;

  function scrollByCard(direction: number) {
    const el = scroller.current;
    if (!el) return;
    const count = visible.length || 1;
    const next = (shown.current + direction + count) % count;
    shown.current = next;
    hold.current = Date.now() + 700;
    setIndex(next);
    const span = loopSpan(el);
    const cards = [...el.querySelectorAll("article")] as HTMLElement[];
    const match = cards.find((card) => Number(card.dataset.slide) === next && card.offsetLeft >= span - 2);
    if (match) el.scrollTo({ left: match.offsetLeft, behavior: "smooth" });
  }

  const slides =
    visible.length > 1
      ? [0, 1, 2].flatMap((copy) => visible.map((url, index) => ({ copy, index, url })))
      : visible.map((url, index) => ({ copy: 0, index, url }));

  return (
    <div className="relative mt-5 aspect-video w-full overflow-hidden rounded-2xl">
      <div
        ref={scroller}
        className="flex h-full snap-x snap-mandatory gap-3 overflow-x-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {slides.map(({ copy, index: slideIndex, url }) => {
          const src = mediaUrl(url);
          if (!src) return null;
          return (
            <article
              key={`${copy}-${slideIndex}`}
              data-slide={slideIndex}
              className="relative h-full w-[90%] shrink-0 snap-start overflow-hidden rounded-xl border border-slate-200 bg-slate-50"
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={src}
                alt={`${name} ${slideIndex + 1}`}
                className="absolute inset-0 h-full w-full object-contain p-4"
              />
            </article>
          );
        })}
      </div>
      {visible.length > 1 ? (
        <>
          <button
            type="button"
            aria-label="Ảnh phía trước"
            className="absolute left-2 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-slate-300 bg-white/90 text-slate-800 shadow-soft transition hover:border-brand-400 hover:text-brand-700"
            onClick={() => scrollByCard(-1)}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} aria-hidden>
              <path d="M15 6l-6 6 6 6" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Ảnh tiếp theo"
            className="absolute right-2 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-full border border-slate-300 bg-white/90 text-slate-800 shadow-soft transition hover:border-brand-400 hover:text-brand-700"
            onClick={() => scrollByCard(1)}
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} aria-hidden>
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        </>
      ) : null}
      {visible.length > 1 ? (
        <p className="pointer-events-none absolute bottom-2 left-4 rounded-full bg-slate-900/75 px-2.5 py-0.5 text-xs font-semibold text-white">
          {index + 1}/{visible.length}
        </p>
      ) : null}
    </div>
  );
}
