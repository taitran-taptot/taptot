"use client";

import Link from "next/link";
import { createPortal } from "react-dom";

export default function CartAddedToast({ message }: { message: string }) {
  if (!message || typeof document === "undefined") return null;
  return createPortal(
    <div
      role="status"
      className="fixed top-20 left-1/2 z-[80] flex w-[min(100%-1.5rem,32rem)] -translate-x-1/2 items-center gap-3 rounded-2xl bg-slate-900 px-4 py-3 text-sm font-semibold text-white shadow-xl"
    >
      <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brand-500" aria-hidden>
        ✓
      </span>
      <span className="min-w-0 flex-1">{message}</span>
      <Link href="/gio-hang" className="shrink-0 text-brand-300 underline underline-offset-4">
        Xem giỏ
      </Link>
    </div>,
    document.body,
  );
}
