"use client";

import type { ReactNode, MouseEvent } from "react";

type Props = {
  href: string;
  className?: string;
  children: ReactNode;
};

function easeInOutCubic(t: number) {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function scrollToEl(el: HTMLElement, durationMs = 900) {
  const headerOffset = 96;
  const startY = window.scrollY;
  const targetY = Math.max(0, el.getBoundingClientRect().top + startY - headerOffset);
  const delta = targetY - startY;
  if (Math.abs(delta) < 2) return;

  const start = performance.now();
  function step(now: number) {
    const t = Math.min(1, (now - start) / durationMs);
    window.scrollTo(0, startY + delta * easeInOutCubic(t));
    if (t < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

/** Same-page hash link with eased smooth scroll (works from Server Component parents). */
export default function SmoothHashLink({ href, className, children }: Props) {
  function onClick(e: MouseEvent<HTMLAnchorElement>) {
    if (!href.startsWith("#")) return;
    const el = document.getElementById(href.slice(1));
    if (!el) return;
    e.preventDefault();
    scrollToEl(el);
    window.history.replaceState(null, "", href);
  }

  return (
    <a href={href} className={className} onClick={onClick}>
      {children}
    </a>
  );
}
