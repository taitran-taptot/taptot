"use client";

import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";

export default function Modal({
  open,
  onClose,
  children,
  size = "md",
  /** When true, modal shell does not scroll — child manages overflow (pickers). */
  lockScroll = false,
  title,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  size?: "md" | "lg" | "xl" | "wide";
  lockScroll?: boolean;
  title?: string;
}) {
  const panelRef = useRef<HTMLDivElement>(null);
  const lastFocus = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    lastFocus.current = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const t = window.setTimeout(() => {
      const first = panelRef.current?.querySelector<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      first?.focus();
    }, 0);
    return () => {
      window.clearTimeout(t);
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
      lastFocus.current?.focus();
    };
  }, [open, onClose]);

  if (!open || typeof document === "undefined") return null;

  const width =
    size === "wide"
      ? "md:w-2/3 md:max-w-none"
      : size === "xl"
        ? "md:max-w-3xl"
        : size === "lg"
          ? "md:max-w-2xl"
          : "md:max-w-lg";

  const labelId = title ? "modal-title" : undefined;

  return createPortal(
    <div className="fixed inset-0 z-[100]" role="dialog" aria-modal="true" aria-labelledby={labelId} aria-label={title || "Hộp thoại"}>
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm"
        aria-label="Đóng"
        onClick={onClose}
      />
      <div className="absolute inset-x-0 bottom-0 flex max-h-[92vh] justify-center p-0 pointer-events-none md:inset-0 md:items-center md:p-4">
        <div
          ref={panelRef}
          className={`pointer-events-auto flex w-full flex-col rounded-t-3xl bg-white shadow-2xl md:rounded-2xl ${width} ${
            lockScroll ? "max-h-[92vh] overflow-hidden" : "max-h-[92vh] overflow-y-auto"
          }`}
        >
          {title ? (
            <h2 id="modal-title" className="sr-only">
              {title}
            </h2>
          ) : null}
          {children}
        </div>
      </div>
    </div>,
    document.body,
  );
}
