"use client";

import { useLayoutEffect, useRef } from "react";
import { DEFAULT_SUCCESS_LOGO, siteImageSrc, type SuccessStory } from "@/lib/sitePageMedia";

function loopSpan(el: HTMLDivElement) {
  const cards = el.querySelectorAll("article");
  const count = cards.length / 3;
  if (count < 1) return 0;
  const start = cards[0] as HTMLElement;
  const next = cards[count] as HTMLElement | undefined;
  if (!next) return 0;
  return next.offsetLeft - start.offsetLeft;
}

export default function SuccessStories({ stories }: { stories: SuccessStory[] }) {
  const scroller = useRef<HTMLDivElement>(null);
  const visible = stories.filter(
    (story) => story.image_url.trim() || story.name.trim() || story.occupation.trim() || story.quote.trim(),
  );

  useLayoutEffect(() => {
    const el = scroller.current;
    if (!el || visible.length < 2) return;
    const place = () => {
      const span = loopSpan(el);
      if (span > 0) el.scrollLeft = span;
    };
    place();

    const settle = () => {
      const span = loopSpan(el);
      if (span <= 0) return;
      if (el.scrollLeft < span - 1) el.scrollLeft += span;
      else if (el.scrollLeft >= span * 2 - 1) el.scrollLeft -= span;
    };
    let timer = 0;
    const onScroll = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(settle, 90);
    };
    el.addEventListener("scroll", onScroll, { passive: true });
    el.addEventListener("scrollend", settle);
    window.addEventListener("resize", place);
    return () => {
      window.clearTimeout(timer);
      el.removeEventListener("scroll", onScroll);
      el.removeEventListener("scrollend", settle);
      window.removeEventListener("resize", place);
    };
  }, [visible.length]);

  if (!visible.length) return null;

  function scrollByCard(direction: number) {
    const el = scroller.current;
    if (!el) return;
    const card = el.querySelector("article");
    const gap = 16;
    const width = card ? card.getBoundingClientRect().width + gap : el.clientWidth / 3;
    el.scrollBy({ left: direction * width, behavior: "smooth" });
  }

  const slides = visible.length > 1 ? [0, 1, 2].flatMap((copy) => visible.map((story, index) => ({ copy, index, story }))) : visible.map((story, index) => ({ copy: 0, index, story }));

  return (
    <section className="rounded-[2rem] border border-slate-100 bg-white px-4 py-8 shadow-soft sm:px-8 sm:py-10">
      <h2 className="type-display mb-5 text-center text-slate-900">Trải nghiệm của mọi người</h2>
      <div
        ref={scroller}
        className="flex snap-x snap-mandatory items-stretch gap-4 overflow-x-auto pb-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {slides.map(({ copy, index, story }) => {
          const logo = story.logo_url.trim() || DEFAULT_SUCCESS_LOGO;
          const brandPhoto = story.image_url.includes("/brand/");
          return (
            <article
              key={`${copy}-${index}-${story.image_url}-${story.name}`}
              className="flex w-[78%] shrink-0 snap-start flex-col overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-soft sm:w-[calc((100%-2rem)/3)]"
            >
              <div className={`card-media-zoom relative aspect-square overflow-hidden ${brandPhoto ? "bg-slate-950" : "bg-slate-100"}`}>
                {story.image_url.trim() ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={siteImageSrc(story.image_url)}
                    alt={story.name.trim() || "Trải nghiệm cùng TAPTOT"}
                    className={`absolute inset-0 h-full w-full ${brandPhoto ? "object-contain p-6" : "object-cover object-top"}`}
                  />
                ) : null}
              </div>
              <div className="flex flex-1 flex-col border-t border-slate-200 px-4 py-4">
                <div className="flex items-center gap-3">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={siteImageSrc(logo)}
                    alt=""
                    className="h-11 w-11 shrink-0 rounded-full border border-slate-200 bg-white object-contain p-1"
                  />
                  <div className="min-w-0">
                    {story.name.trim() ? <h3 className="truncate text-base font-bold text-slate-950">{story.name.trim()}</h3> : null}
                    {story.occupation.trim() ? (
                      <p className="mt-0.5 truncate text-sm font-semibold text-brand-700">{story.occupation.trim()}</p>
                    ) : null}
                  </div>
                </div>
                {story.quote.trim() ? (
                  <p className="mt-3 border-t border-slate-100 pt-3 text-sm font-medium leading-relaxed text-slate-800">
                    “{story.quote.trim()}”
                  </p>
                ) : null}
              </div>
            </article>
          );
        })}
      </div>
      {visible.length > 1 ? (
        <div className="mt-5 flex justify-center gap-3">
          <button
            type="button"
            aria-label="Xem người phía trước"
            className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-800 shadow-soft transition hover:border-brand-400 hover:text-brand-700"
            onClick={() => scrollByCard(-1)}
          >
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} aria-hidden>
              <path d="M15 6l-6 6 6 6" />
            </svg>
          </button>
          <button
            type="button"
            aria-label="Xem người tiếp theo"
            className="inline-flex h-12 w-12 items-center justify-center rounded-full border border-slate-300 bg-white text-slate-800 shadow-soft transition hover:border-brand-400 hover:text-brand-700"
            onClick={() => scrollByCard(1)}
          >
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.4} aria-hidden>
              <path d="M9 6l6 6-6 6" />
            </svg>
          </button>
        </div>
      ) : null}
    </section>
  );
}
